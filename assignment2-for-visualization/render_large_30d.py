"""Render a larger-resolution animation using the most recent ~30 days of data.

- Loads `assignment2-for-visualization/rain_by_station_90days.csv` (the pivot produced earlier).
- Selects the most recent 30 calendar days that have data; if the pivot has fewer rows, repeats/loops to reach ~30 days.
- Calls `render_animation_fast` at larger size (1600x1600) and slightly slower FPS for a longer feeling.
"""
from pathlib import Path
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, str(Path('.').resolve()))
from merge_and_render_rain import render_animation_fast

csvp = Path('assignment2-for-visualization/rain_by_station_90days.csv')
if not csvp.exists():
    print('CSV not found at', csvp)
    raise SystemExit(1)

pivot = pd.read_csv(csvp, index_col=0, parse_dates=True)
pivot.index = [d.date() for d in pd.to_datetime(pivot.index)]
print('Loaded pivot shape', pivot.shape)

# choose ~30 most recent rows that contain non-zero station data if possible
recent = pivot.dropna(how='all')
# filter rows that have any non-zero rainfall across stations
has_nonzero = recent.loc[(recent.sum(axis=1) > 0)] if not recent.empty else recent
if not has_nonzero.empty:
    # take last 30 days with any values
    sel = has_nonzero.tail(30)
else:
    # fallback: take last 30 calendar rows from pivot
    sel = pivot.tail(30)

# if we have fewer than 30 rows, repeat the series to reach 30
if len(sel) < 30:
    rows = []
    while len(rows) < 30:
        rows.extend(list(sel.to_dict(orient='index').values()))
    # build DataFrame with repeated rows and a synthetic date index
    sel = pd.DataFrame(rows[:30])
    # create synthetic dates
    from datetime import date, timedelta
    today = date.today()
    idx = [today - timedelta(days=(29-i)) for i in range(30)]
    sel.index = idx

print('Rendering', len(sel), 'days at large resolution')
# render larger (1600x1600), 12 subframes/day, mp4 at 10 fps for longer duration
render_animation_fast(sel, out_gif='ripple_enhanced_30d_1600.gif', out_mp4='ripple_enhanced_30d_1600.mp4', frames_per_day=12, gamma=1.5, amp_scale=6.0, size=(1600,1600), mp4_fps=10)
print('Done: ripple_enhanced_30d_1600.{gif,mp4}')
