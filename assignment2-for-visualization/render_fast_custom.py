"""Load existing pivot CSV and re-render using faster/more frames per day for smoother ripple animation."""
from pathlib import Path
import pandas as pd
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
# stronger motion: 12 subframes/day, slightly lower gamma, higher amp
render_animation_fast(pivot, out_gif='ripple_enhanced_fromcsv_fast.gif', out_mp4='ripple_enhanced_fromcsv_fast.mp4', frames_per_day=12, gamma=1.5, amp_scale=6.0)
print('Done')
