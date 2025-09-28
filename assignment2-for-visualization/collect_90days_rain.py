"""Collect 90 days of daily DYN_DAT_MINDS_RHRREAD JSON and build a station x date CSV.

Usage: run inside the project's venv. It will write:
- rain_by_station_90days.csv
- rain_by_station_90days_sample.json (a small JSON for inspection)
"""
from pathlib import Path
import requests, json
from datetime import date, timedelta, datetime
import time
import pandas as pd

OUT_CSV = Path('assignment2-for-visualization/rain_by_station_90days.csv')
OUT_SAMPLE = Path('assignment2-for-visualization/rain_by_station_90days_sample.json')

base = 'https://my.weather.gov.hk/json/DYN_DAT_MINDS_RHRREAD.json'

today = date.today()
DAYS = 90
rows = []
for i in range(DAYS):
    d = today - timedelta(days=i)
    dstr = d.strftime('%Y%m%d')
    url = f'{base}?date={dstr}'
    print('GET', url)
    try:
        r = requests.get(url, timeout=12)
        if r.status_code != 200:
            print('  status', r.status_code)
            continue
        j = r.json()
        root = j.get('DYN_DAT_MINDS_RHRREAD') or j.get(next(iter(j.keys())))
        # collect keys ending with RainfallValue, Rainfall, or *RainfallValue* etc.
        for key, val in (root.items() if isinstance(root, dict) else []):
            if key.lower().endswith('rainfallvalue') or 'rainfall' in key.lower():
                # get station name
                loc_key = key.replace('RainfallValue', 'LocationName')
                loc = None
                if isinstance(root.get(loc_key), dict):
                    loc = root.get(loc_key).get('Val_Eng') or root.get(loc_key).get('Val_Chi')
                # extract numeric
                vnum = None
                if isinstance(val, dict):
                    vstr = val.get('Val_Eng') or val.get('Val_Chi')
                    try:
                        vnum = float(vstr) if vstr not in (None, '') else None
                    except Exception:
                        vnum = None
                else:
                    try:
                        vnum = float(val)
                    except Exception:
                        vnum = None
                if vnum is not None:
                    rows.append({'date': d, 'station': str(loc or key), 'value': vnum})
    except Exception as e:
        print('  error', e)
    time.sleep(0.15)

if not rows:
    print('No rows collected')
else:
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date']).dt.date
    pivot = df.pivot_table(index='date', columns='station', values='value', aggfunc='sum', fill_value=0)
    pivot = pivot.sort_index(ascending=True)
    pivot.to_csv(OUT_CSV)
    print('Wrote', OUT_CSV, 'shape', pivot.shape)
    # save small sample JSON
    # pivot.index may already be datetime.date objects; convert to ISO strings
    sample = {'dates': [str(d) for d in pivot.index[:10]], 'stations': list(pivot.columns[:10])}
    OUT_SAMPLE.write_text(json.dumps(sample, indent=2), encoding='utf-8')
    print('Wrote sample JSON to', OUT_SAMPLE)
