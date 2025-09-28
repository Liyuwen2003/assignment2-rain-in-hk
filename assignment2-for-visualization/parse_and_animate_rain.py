"""Parse HKO one_json_uc content and produce a ripple animation (GIF) based on 90-day totals.

This script tries to extract per-station daily rainfall records from the JSON structure
and then constructs a frame-per-day ripple visualization which is saved as `ripple_animation.gif`.
"""
from __future__ import annotations

import json
import re
import math
import hashlib
import random
import datetime
from typing import Dict, Any

import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image


def fetch_one_json():
    url = 'https://my.weather.gov.hk/wxinfo/json/one_json_uc.xml'
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    # content is actually JSON inside XML wrapper sometimes; try json.loads
    txt = r.text
    try:
        return json.loads(txt)
    except Exception:
        # try to extract JSON substring
        m = re.search(r'\{\s*"FLW".*', txt, re.S)
        if m:
            jtxt = m.group(0)
            # attempt to trim trailing characters
            # find last closing brace that balances
            depth = 0
            end = None
            for i, ch in enumerate(jtxt):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end:
                jtxt2 = jtxt[:end+1]
                try:
                    return json.loads(jtxt2)
                except Exception:
                    pass
    raise RuntimeError('Failed to parse one_json_uc content')


def find_timeseries_in_json(j: Dict[str, Any]):
    # Heuristic: look for nested dicts/lists containing date-like keys or records
    date_re = re.compile(r'20\d{2}[01]\d[0-3]\d|\d{4}-\d{2}-\d{2}')
    candidates = []

    def walk(obj, path=''):
        if isinstance(obj, dict):
            # date-like keys
            if any(date_re.search(k) for k in list(obj.keys())[:200]):
                candidates.append((path, obj))
            for k, v in obj.items():
                walk(v, path + '/' + k)
        elif isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                # maybe list of records
                # check for date and numeric fields
                sample = obj[0]
                if any('date' in kk.lower() or date_re.search(kk) for kk in sample.keys()):
                    candidates.append((path, obj))
            for i, it in enumerate(obj[:50]):
                walk(it, path + f'[{i}]')

    walk(j)
    return candidates


def build_dataframe_from_candidate(path, obj):
    # return DataFrame with columns: date, station, value OR wide-format date x station
    if isinstance(obj, dict):
        # dict keyed by date -> maybe station:value map or single value
        records = []
        for k, v in obj.items():
            date = None
            try:
                # try parse yyyymmdd or yyyy-mm-dd
                if re.match(r'\d{8}$', k):
                    date = datetime.datetime.strptime(k, '%Y%m%d').date()
                elif re.match(r'\d{4}-\d{2}-\d{2}$', k):
                    date = datetime.datetime.strptime(k, '%Y-%m-%d').date()
            except Exception:
                date = None
            if date is None:
                continue
            if isinstance(v, dict):
                for st, val in v.items():
                    try:
                        valn = float(val)
                    except Exception:
                        continue
                    records.append({'date': date, 'station': st, 'value': valn})
            else:
                try:
                    valn = float(v)
                    records.append({'date': date, 'station': 'global', 'value': valn})
                except Exception:
                    continue
        if records:
            return pd.DataFrame(records)
    elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
        # list of records; try to find date key and value key
        sample = obj[0]
        date_key = None
        value_key = None
        for k in sample.keys():
            if 'date' in k.lower() or re.match(r'date|time', k.lower()):
                date_key = k
        for k in sample.keys():
            if k == date_key:
                continue
            v = sample.get(k)
            if isinstance(v, (int, float)) or (isinstance(v, str) and re.match(r'^\s*[0-9.+-]', str(v))):
                value_key = k
                break
        records = []
        if date_key and value_key:
            for rec in obj:
                try:
                    dstr = rec.get(date_key)
                    if re.match(r'\d{8}$', str(dstr)):
                        date = datetime.datetime.strptime(str(dstr), '%Y%m%d').date()
                    else:
                        date = datetime.datetime.strptime(str(dstr)[:10], '%Y-%m-%d').date()
                except Exception:
                    continue
                try:
                    v = float(rec.get(value_key, 0))
                except Exception:
                    continue
                st = rec.get('station') or rec.get('site') or rec.get('station_id') or 'site'
                records.append({'date': date, 'station': st, 'value': v})
            if records:
                return pd.DataFrame(records)
    return pd.DataFrame()


def aggregate_90_days(df: pd.DataFrame):
    if df.empty:
        return {}
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=90)
    df2 = df[df['date'] >= cutoff]
    agg = df2.groupby('station')['value'].sum().to_dict()
    return agg


def make_animation_from_totals_by_day(df: pd.DataFrame, outpath='ripple_animation.gif'):
    # build daily totals per station for the last 90 days
    today = datetime.date.today()
    start = today - datetime.timedelta(days=89)
    days = [start + datetime.timedelta(days=i) for i in range(90)]

    frames = []
    for d in days:
        df_day = df[df['date'] == d]
        totals = df_day.groupby('station')['value'].sum().to_dict()
        im = draw_ripple_frame(totals, title=f'Date: {d.isoformat()}')
        frames.append(im)

    # save as GIF
    frames[0].save(outpath, save_all=True, append_images=frames[1:], duration=200, loop=0)
    print('Saved animation to', outpath)


def draw_ripple_frame(totals: Dict[str, float], title=''):
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    ax.set_facecolor('#f7fcff')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:200]
    if not items:
        # empty frame placeholder
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
    else:
        vals = [v for k, v in items]
        vmin = min(vals)
        vmax = max(vals)
        norm = lambda x: 0.0 + 1.0 * ((x - vmin) / (vmax - vmin) if vmax > vmin else 0.5)
        random.seed(123)
        for key, val in items:
            t = norm(val)
            h = hashlib.sha1(key.encode()).hexdigest()
            x = (int(h[:8], 16) % 1000) / 1000
            y = (int(h[8:16], 16) % 1000) / 1000
            x = min(max(x + (random.random() - 0.5) * 0.03, 0.02), 0.98)
            y = min(max(y + (random.random() - 0.5) * 0.03, 0.02), 0.98)
            n = int(2 + 6 * t)
            base = 0.02 + 0.18 * t
            spacing = 0.02 + 0.02 * (1 - t)
            col = (0.84*(1-t)+0.04*t, 0.94*(1-t)+0.15*t, 0.99*(1-t)+0.57*t)
            for i in range(n):
                rads = base + i * spacing
                alpha = max(0.02, (1.0/(1+i)) * (0.6 + 0.4 * t))
                circ = Circle((x, y), rads, linewidth=1.0, edgecolor=col, facecolor='none', alpha=alpha)
                ax.add_patch(circ)

    ax.set_title(title, fontsize=10)
    plt.tight_layout()
    # convert to PIL image
    from io import BytesIO
    buf = BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert('P')
    return im


def main():
    j = fetch_one_json()
    candidates = find_timeseries_in_json(j)
    print('Found', len(candidates), 'candidates')
    # try to build dataframe from first good candidate
    df = None
    for path, obj in candidates:
        print('Trying candidate path', path, 'type', type(obj))
        df_try = build_dataframe_from_candidate(path, obj)
        if not df_try.empty:
            df = df_try
            break

    if df is None or df.empty:
        print('Could not build dataframe from candidates; aborting')
        return

    print('Built dataframe with rows:', len(df))
    # normalize columns
    df['date'] = pd.to_datetime(df['date']).dt.date
    # generate animation
    make_animation_from_totals_by_day(df, outpath='ripple_animation.gif')


if __name__ == '__main__':
    main()
