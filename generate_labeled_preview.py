"""Generate a labeled preview MP4 and GIF that explicitly overlays station names.

Outputs:
- ripple_labeled_preview_1600.mp4
- ripple_labeled_preview_1600.gif

This script recomputes deterministic positions for station labels to ensure they appear.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import hashlib
from datetime import date, timedelta

# ensure repo path imports the rendering utilities
import sys
sys.path.insert(0, str(Path('assignment2-for-visualization').resolve()))
from merge_and_render_rain import draw_frame_image

OUT_MP4 = Path('ripple_labeled_preview_1600.mp4')
OUT_GIF = Path('ripple_labeled_preview_1600.gif')
CSV = Path('assignment2-for-visualization/rain_by_station_90days.csv')

if not CSV.exists():
    raise SystemExit('Pivot CSV not found: ' + str(CSV))

pivot = pd.read_csv(CSV, index_col=0, parse_dates=True)
pivot.index = [d.date() for d in pd.to_datetime(pivot.index)]

# pick recent 30 days with any non-zero values if possible
recent = pivot[(pivot.sum(axis=1) > 0)]
if not recent.empty:
    sel = recent.tail(30)
else:
    sel = pivot.tail(30)

# ensure 30 rows
if len(sel) < 30:
    rows = []
    while len(rows) < 30:
        rows.extend(list(sel.to_dict(orient='index').values()))
    sel = pd.DataFrame(rows[:30])
    today = date.today()
    sel.index = [today - timedelta(days=(29-i)) for i in range(30)]

# render params
size = (1600, 1600)
frames_per_day = 6
mp4_fps = 8
amp_scale = 6.0
gamma = 1.5

from PIL import Image
frames = []

stations = list(sel.columns)

for d in sel.index:
    row = sel.loc[d].to_dict()
    # compute simple weights from row (normalize)
    vals = np.array([float(row.get(st, 0.0) or 0.0) for st in stations], dtype=float)
    vmax = vals.max() if vals.max() > 0 else 1.0
    # delta approach omitted here; just use values
    weights = {st: ((float(row.get(st, 0.0) or 0.0) / vmax) ** gamma) for st in stations}

    for f in range(frames_per_day):
        phase = f / frames_per_day
        # draw base image (with internal overlay too)
        im = draw_frame_image(weights, size=size, phase=phase, amp=amp_scale, title='香港各区降水量', date_text=str(d))
        # now explicitly overlay station labels at deterministic positions to guarantee visibility
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(im)
        try:
            # larger label font for readability
            lab_font = ImageFont.truetype('DejaVuSans.ttf', 28)
        except Exception:
            lab_font = None

        # compute deterministic positions using same hash logic
        for st in stations:
            hsh = hashlib.sha1(st.encode()).hexdigest()
            x = (int(hsh[:8], 16) % 1000) / 1000
            y = (int(hsh[8:16], 16) % 1000) / 1000
            # scale to image coordinates (note: draw_frame uses a small jitter; we skip jitter so labels are stable)
            px = int(x * im.width)
            py = int((1.0 - y) * im.height)
            fx = px + 8
            fy = py - 8
            # draw shadow + text
            draw.text((fx+1, fy+1), st, font=lab_font, fill=(0,0,0,200))
            draw.text((fx, fy), st, font=lab_font, fill=(240,245,255,230))

        frames.append(im.convert('P'))

# save GIF
frames[0].save(OUT_GIF, save_all=True, append_images=frames[1:], duration=int(1000/mp4_fps), loop=0)
print('Saved', OUT_GIF)

# save MP4 via imageio
try:
    import imageio
    with imageio.get_writer(OUT_MP4, fps=mp4_fps) as writer:
        for im in frames:
            writer.append_data(np.array(im.convert('RGB')))
    print('Saved', OUT_MP4)
except Exception as e:
    print('MP4 export failed:', e)

print('Done')
