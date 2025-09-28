"""Merge time-series from captured endpoints and render an enhanced ripple animation.

Features:
- Scan `network_candidates_deep.txt` for JSON-like endpoints.
- Extract per-station/date/value records with heuristics.
- Merge into one DataFrame and compute 90-day totals and daily frames.
- Render high-res frames with gradient-filled ripples, apply light Gaussian blur for softness.
- Save `ripple_enhanced.gif` and (if ffmpeg available) `ripple_enhanced.mp4`.
"""
from __future__ import annotations

import json
import re
import math
import hashlib
import random
import datetime
from pathlib import Path
from typing import Dict, Any

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image, ImageFilter, ImageDraw, ImageFont


DATE_RE = re.compile(r'20\d{2}-\d{2}-\d{2}|\d{8}')


def load_candidates(path='network_candidates_deep.txt'):
    p = Path(path)
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]


def try_parse_json_text(txt: str):
    try:
        return json.loads(txt)
    except Exception:
        return None


def extract_timeseries_from_obj(obj, path=''):
    # Heuristics similar to earlier scripts: look for dict keyed by date mapping to stations or list of records
    res_frames = []

    def build_df_from_date_dict(d: Dict[str, Any]):
        rows = []
        for k, v in d.items():
            # parse date key
            dt = None
            try:
                if re.match(r'^\d{8}$', k):
                    dt = datetime.datetime.strptime(k, '%Y%m%d').date()
                elif re.match(r'^\d{4}-\d{2}-\d{2}$', k):
                    dt = datetime.datetime.strptime(k, '%Y-%m-%d').date()
            except Exception:
                dt = None
            if dt is None:
                continue
            if isinstance(v, dict):
                for st, val in v.items():
                    try:
                        valn = float(val)
                    except Exception:
                        continue
                    rows.append({'date': dt, 'station': str(st), 'value': valn})
            else:
                try:
                    valn = float(v)
                    rows.append({'date': dt, 'station': 'global', 'value': valn})
                except Exception:
                    continue
        if rows:
            return pd.DataFrame(rows)
        return pd.DataFrame()

    def walk(o, curpath=''):
        if isinstance(o, dict):
            # if keys look like dates
            keys = list(o.keys())[:200]
            if any(DATE_RE.search(str(k)) for k in keys):
                df = build_df_from_date_dict(o)
                if not df.empty:
                    res_frames.append(df)
            for k, v in list(o.items())[:200]:
                walk(v, curpath + '/' + str(k))
        elif isinstance(o, list):
            # list of records
            if o and isinstance(o[0], dict):
                # try to identify date and value keys
                sample = o[0]
                date_key = None
                val_key = None
                for kk in sample.keys():
                    if 'date' in kk.lower() or DATE_RE.search(str(kk)):
                        date_key = kk
                for kk in sample.keys():
                    if kk == date_key:
                        continue
                    sv = sample.get(kk)
                    if isinstance(sv, (int, float)) or (isinstance(sv, str) and re.match(r'^\s*[0-9.+-]', str(sv))):
                        val_key = kk
                        break
                if date_key and val_key:
                    rows = []
                    for rec in o:
                        try:
                            dstr = rec.get(date_key)
                            if dstr is None:
                                continue
                            d = None
                            if re.match(r'^\d{8}$', str(dstr)):
                                d = datetime.datetime.strptime(str(dstr), '%Y%m%d').date()
                            else:
                                d = datetime.datetime.strptime(str(dstr)[:10], '%Y-%m-%d').date()
                        except Exception:
                            continue
                        try:
                            v = float(rec.get(val_key, 0))
                        except Exception:
                            continue
                        st = rec.get('station') or rec.get('site') or rec.get('station_id') or rec.get('id') or 'site'
                        rows.append({'date': d, 'station': str(st), 'value': v})
                    if rows:
                        res_frames.append(pd.DataFrame(rows))
            for i, it in enumerate(o[:200]):
                walk(it, curpath + f'[{i}]')

    walk(obj, path)
    return res_frames


def extract_from_url(u: str):
    try:
        r = requests.get(u, timeout=12)
    except Exception:
        return []
    txt = r.text
    j = try_parse_json_text(txt)
    frames = []
    if j is not None:
        # Special-case: DYN_DAT_MINDS_RHRREAD responses have a lot of district/zone keys
        if isinstance(j, dict) and any(k.startswith('DYN_DAT_MINDS_RHRREAD') for k in j.keys()):
            root = j.get('DYN_DAT_MINDS_RHRREAD') or j.get(next(iter(j.keys())))
            # parse district/station rainfall fields
            rows = []
            # keys like 'CentralAndWesternDistrictRainfallValue' and 'CentralAndWesternDistrictLocationName'
            for key, val in (root.items() if isinstance(root, dict) else []):
                if key.endswith('RainfallValue') or key.endswith('Rainfall'):
                    loc_key = key.replace('RainfallValue', 'LocationName').replace('Rainfall', 'LocationName')
                    loc = None
                    if isinstance(root.get(loc_key), dict):
                        loc = root.get(loc_key).get('Val_Eng') or root.get(loc_key).get('Val_Chi')
                    # val may be dict with Val_Eng/Val_Chi
                    vstr = None
                    if isinstance(val, dict):
                        vstr = val.get('Val_Eng') or val.get('Val_Chi')
                    elif isinstance(val, (str, int, float)):
                        vstr = str(val)
                    try:
                        vnum = float(vstr) if vstr not in (None, '') else None
                    except Exception:
                        vnum = None
                    if vnum is not None:
                        rows.append({'date': None, 'station': str(loc or key), 'value': vnum})
            if rows:
                # this source is per-date, so try to extract date from ObservationsObsTime or similar
                obs = root.get('ObservationsObsTime') or root.get('ObservationsObsTimeAll') or {}
                dateval = None
                if isinstance(obs, dict):
                    s = obs.get('Val_Eng') or obs.get('Val_Chi')
                    if s:
                        try:
                            # often like YYYYMMDDhhmm
                            dateval = datetime.datetime.strptime(str(s)[:8], '%Y%m%d').date()
                        except Exception:
                            dateval = None
                for rrow in rows:
                    rrow['date'] = dateval or datetime.date.today()
                frames = [pd.DataFrame(rows)]
        else:
            frames = extract_timeseries_from_obj(j, path=u)
    else:
        # maybe XML that contains JSON substring
        m = re.search(r'\{\s*"FLW".*', txt, re.S)
        if m:
            try:
                j2 = json.loads(m.group(0))
                frames = extract_timeseries_from_obj(j2, path=u)
            except Exception:
                pass
    return frames


def merge_frames(frames_list):
    if not frames_list:
        return pd.DataFrame(columns=['date', 'station', 'value'])
    df = pd.concat(frames_list, ignore_index=True)
    # coerce types
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['station'] = df['station'].astype(str)
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value'])
    return df


def compute_daily_totals(df: pd.DataFrame, days=90):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=days-1)
    rng = [start + datetime.timedelta(days=i) for i in range(days)]
    # pivot: index=date, columns=station, values=sum
    df2 = df[(df['date'] >= start) & (df['date'] <= today)]
    if df2.empty:
        return pd.DataFrame(index=rng)
    pivot = df2.pivot_table(index='date', columns='station', values='value', aggfunc='sum', fill_value=0)
    # reindex to full date range
    pivot = pivot.reindex(rng, fill_value=0)
    return pivot


def draw_frame_image(totals: Dict[str, float], size=(1200, 900), phase: float = 0.0, amp: float = 1.0, title: str = None, date_text: str = None):
    # Create a high-res frame with filled gradient ripples and soft blur
    w, h = size
    fig, ax = plt.subplots(figsize=(w/100, h/100), dpi=100)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    # totals is a mapping station->weight in linear space
    items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:250]
    if items:
        # filter non-finite values and ensure safe min/max
        vals = [float(v) if np.isfinite(v) else 0.0 for k, v in items]
        try:
            vmin = float(np.min(vals))
        except Exception:
            vmin = 0.0
        try:
            vmax = float(np.max(vals))
        except Exception:
            vmax = 1.0
        # handle degenerate case
        if not np.isfinite(vmin):
            vmin = 0.0
        if not np.isfinite(vmax) or vmax <= vmin:
            def norm(x):
                return 0.5
        else:
            def norm(x):
                try:
                    return float((x - vmin) / (vmax - vmin))
                except Exception:
                    return 0.0
        random.seed(42)
        # background gradient
        grad = np.linspace(0, 1, 256)
        bg = np.vstack([np.linspace(30/255, 6/255, 256)]*256)
        ax.imshow(np.tile(np.linspace(0,1,256), (256,1)), extent=(0,1,0,1), origin='lower', cmap=plt.get_cmap('Blues'), alpha=0.12)

        label_positions = []
        for key, val in items:
            # apply amplitude and phase: phase in [0,1] animates radius/intensity
            t = norm(val * amp)
            # ensure t is finite and clamped to [0,1]
            try:
                t = float(t)
            except Exception:
                t = 0.0
            if not np.isfinite(t):
                t = 0.0
            t = max(0.0, min(1.0, t))
            hsh = hashlib.sha1(key.encode()).hexdigest()
            x = (int(hsh[:8], 16) % 1000) / 1000
            y = (int(hsh[8:16], 16) % 1000) / 1000
            x = min(max(x + (random.random() - 0.5) * 0.02, 0.02), 0.98)
            y = min(max(y + (random.random() - 0.5) * 0.02, 0.02), 0.98)
            n = int(3 + 8 * t)
            # animate base radius with phase to create pulsing
            base = 0.02 + 0.22 * t * (0.7 + 0.6 * (0.5 + 0.5 * math.sin(2 * math.pi * phase)))
            spacing = 0.02 + 0.02 * (1 - t)
            # color gradient: from light to deep blue based on t
            c1 = np.array([215, 238, 251]) / 255.0
            c2 = np.array([11, 61, 145]) / 255.0
            col = c1 * (1 - t) + c2 * t
            # ensure color components are in 0-1 range
            col = np.clip(col, 0.0, 1.0)
            for i in range(n):
                # slightly offset radius per-frame to simulate ripple motion
                rads = base + i * spacing * (1.0 + 0.15 * math.sin(2 * math.pi * (phase + i * 0.08)))
                alpha = max(0.01, math.exp(-0.55 * i) * (0.9 * t + 0.08))
                # clamp alpha to valid matplotlib range
                if not np.isfinite(alpha):
                    alpha = 0.01
                alpha = max(0.0, min(1.0, alpha))
                circ = Circle((x, y), rads, linewidth=1.2, edgecolor=col, facecolor=col, alpha=alpha)
                ax.add_patch(circ)
            # remember label positions (normalized coordinates)
            label_positions.append((key, x, y, t))
        # subtle noise overlay
        import numpy.random as npr
        noise = (npr.randn(int(h/4), int(w/4)) * 6 + 120).clip(0,255).astype('uint8')
        # we'll composite noise later via PIL
    else:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', fontsize=24)

    fig.tight_layout(pad=0)
    from io import BytesIO
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    im = Image.open(buf).convert('RGBA')
    # soft blur for artistic look
    im = im.filter(ImageFilter.GaussianBlur(radius=2))
    # add faint film-grain
    try:
        import numpy as _np
        arr = _np.array(im)
        gh = _np.random.normal(0, 6, (arr.shape[0], arr.shape[1], 1)).astype('int16')
        arr2 = _np.clip(arr.astype('int16') + gh, 0, 255).astype('uint8')
        im = Image.fromarray(arr2, mode='RGBA')
    except Exception:
        pass
    # overlay labels and title/date after blur so text is crisp
    try:
        draw = ImageDraw.Draw(im)
        # scale fonts by image size
        scale = float(im.width) / 900.0
        try:
            title_font = ImageFont.truetype('DejaVuSans.ttf', int(36 * scale))
            date_font = ImageFont.truetype('DejaVuSans.ttf', int(26 * scale))
            lab_font = ImageFont.truetype('DejaVuSans.ttf', int(14 * scale))
        except Exception:
            title_font = None
            date_font = None
            lab_font = None

        # draw title at top-center
        if title:
            txt = title
            w, h = draw.textsize(txt, font=title_font)
            x0 = (im.width - w) // 2
            y0 = int(12 * scale)
            # shadow
            draw.text((x0+2, y0+2), txt, font=title_font, fill=(0,0,0,200))
            draw.text((x0, y0), txt, font=title_font, fill=(230,245,255,255))

        # draw station labels (only a subset to avoid clutter) - show top N by weight
        max_labels = 40
        for lab, x, y, t in label_positions[:max_labels]:
            px = int(x * im.width)
            py = int((1.0 - y) * im.height)
            # offset label slightly to the right and upward
            fx = px + int(8 * scale)
            fy = py - int(8 * scale)
            # shadow then main
            draw.text((fx+1, fy+1), str(lab), font=lab_font, fill=(0,0,0,200))
            draw.text((fx, fy), str(lab), font=lab_font, fill=(220,235,255,230))

        # draw date in bottom-left larger
        if date_text:
            txt = date_text
            w, h = draw.textsize(txt, font=date_font)
            dx = int(18 * scale)
            dy = im.height - h - int(18 * scale)
            draw.text((dx+2, dy+2), txt, font=date_font, fill=(0,0,0,200))
            draw.text((dx, dy), txt, font=date_font, fill=(220,235,255,255))
    except Exception:
        pass

    return im


def render_animation_fast(pivot: pd.DataFrame, out_gif='ripple_fast.gif', out_mp4='ripple_fast.mp4', frames_per_day: int = 6, gamma: float = 1.8, amp_scale: float = 4.0, size=(900,900), mp4_fps: int = 12):
    # Build per-day frames with multiple subframes per date to make motion visible.
    frames = []
    days = list(pivot.index)
    if not days:
        print('No daily data to render (fast)')
        return

    # compute normalized values across all days and stations to amplify small differences
    vals = pivot.values.astype(float)
    if vals.size == 0:
        print('Empty pivot values')
        return
    # normalize per-station globally
    vmax = vals.max() if vals.max() > 0 else 1.0

    # compute day-to-day deltas to emphasize change
    delta = pivot.diff().abs().fillna(0)
    dmax = delta.values.max() if delta.values.max() > 0 else 1.0

    for di, d in enumerate(days):
        row = pivot.loc[d].to_dict()
        delta_row = delta.loc[d].to_dict() if d in delta.index else {k: 0.0 for k in pivot.columns}
        # compute combined weight per station (sanitized)
        weights = {}
        for st in pivot.columns:
            try:
                v = float(row.get(st, 0.0))
            except Exception:
                v = 0.0
            try:
                dv = float(delta_row.get(st, 0.0))
            except Exception:
                dv = 0.0
            # clamp to non-negative
            if not (v >= 0):
                v = 0.0
            if not (dv >= 0):
                dv = 0.0
            try:
                nv = (v / vmax) ** gamma if vmax and vmax > 0 else 0.0
            except Exception:
                nv = 0.0
            try:
                nd = (dv / dmax) ** gamma if dmax and dmax > 0 else 0.0
            except Exception:
                nd = 0.0
            if not np.isfinite(nv):
                nv = 0.0
            if not np.isfinite(nd):
                nd = 0.0
            w = 0.6 * nv + 1.8 * nd
            weights[st] = w

        # small global amplification to make tiny weights visible
        global_amp = amp_scale
        for f in range(frames_per_day):
            phase = f / frames_per_day
            # pass title/date_text for overlay
            im = draw_frame_image(weights, size=size, phase=phase, amp=global_amp, title='香港各区降水量', date_text=str(d))
            # annotate
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(im)
            try:
                font = ImageFont.truetype('DejaVuSans.ttf', 18)
            except Exception:
                font = None
            txt = str(d)
            draw.text((18, 18), txt, fill=(20, 30, 60, 240), font=font)
            frames.append(im.convert('P'))

    # save GIF (duration per frame in ms). Use mp4_fps as reference to keep playback consistent.
    try:
        duration_ms = int(1000.0 / mp4_fps)
    except Exception:
        duration_ms = int(200 / frames_per_day)
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=duration_ms, loop=0)
    print('Saved', out_gif)

    # MP4 via imageio
    try:
        import imageio
        with imageio.get_writer(out_mp4, fps=mp4_fps) as writer:
            for im in frames:
                writer.append_data(np.array(im.convert('RGB')))
        print('Saved', out_mp4)
    except Exception as e:
        print('MP4 export skipped (imageio/ffmpeg missing or error):', e)


def render_animation(pivot: pd.DataFrame, out_gif='ripple_enhanced.gif', out_mp4='ripple_enhanced.mp4'):
    frames = []
    days = list(pivot.index)
    if not days:
        print('No daily data to render')
        return
    for d in days:
        row = pivot.loc[d].to_dict()
        im = draw_frame_image(row, size=(1200, 900), title='香港各区降水量', date_text=d.isoformat())
        # annotate date (fonts imported at top)
        draw = ImageDraw.Draw(im)
        try:
            font = ImageFont.truetype('DejaVuSans.ttf', 24)
        except Exception:
            font = None
        txt = d.isoformat()
        draw.text((20, 20), txt, fill=(20, 30, 60, 220), font=font)
        frames.append(im.convert('P'))

    # save GIF
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=250, loop=0)
    print('Saved', out_gif)

    # try MP4 via imageio if available
    try:
        import imageio
        with imageio.get_writer(out_mp4, fps=4) as writer:
            for im in frames:
                writer.append_data(np.array(im.convert('RGB')))
        print('Saved', out_mp4)
    except Exception as e:
        print('MP4 export skipped (imageio/ffmpeg missing or error):', e)


def main():
    # If a pre-collected 90-day CSV exists, use it directly (fast path)
    csvp = Path('assignment2-for-visualization/rain_by_station_90days.csv')
    if not csvp.exists():
        csvp = Path('rain_by_station_90days.csv')
    if csvp.exists():
        print('Found pre-collected CSV at', str(csvp))
        try:
            pivot = pd.read_csv(csvp, index_col=0, parse_dates=True)
            pivot.index = [d.date() for d in pd.to_datetime(pivot.index)]
            print('Loaded pivot from CSV, shape', pivot.shape)
            render_animation(pivot, out_gif='ripple_enhanced_fromcsv.gif', out_mp4='ripple_enhanced_fromcsv.mp4')
            return
        except Exception as e:
            print('Failed to load CSV pivot:', e)

    cands = load_candidates()
    print('Loaded', len(cands), 'candidates')
    interesting = [u for u in cands if any(x in u.lower() for x in ['.json','/wxinfo/','rain','isoh','dyn_dat','/json/','/wwi/'])]
    print('Filtering to', len(interesting), 'interesting candidates')

    extracted = []
    for u in interesting:
        frames = extract_from_url(u)
        if frames:
            print('Extracted', len(frames), 'frames from', u)
            extracted.extend(frames)

    if not extracted:
        print('No timeseries frames extracted; aborting')
        return

    df = merge_frames(extracted)
    print('Merged dataframe rows:', len(df))
    pivot = compute_daily_totals(df, days=90)
    print('Pivot shape', pivot.shape)
    render_animation(pivot, out_gif='ripple_enhanced.gif', out_mp4='ripple_enhanced.mp4')


if __name__ == '__main__':
    main()
