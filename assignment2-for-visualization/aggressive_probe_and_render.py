"""Aggressive probe: try daily dates for common param names across candidate URLs
Collect per-station rows for last 90 days, write pivot CSV, then render animation.

Outputs:
- assignment2-for-visualization/rain_by_station_90days_expanded2.csv
- updates assignment2-for-visualization/rain_by_station_90days.csv (temporarily)
- generates ripple_enhanced_fromcsv.gif and .mp4 via merge_and_render_rain.py
"""
from pathlib import Path
import requests, json, re
from datetime import date, timedelta, datetime
import time
import pandas as pd

ROOT = Path('assignment2-for-visualization')
ROOT.mkdir(exist_ok=True)
OUT_CSV2 = ROOT / 'rain_by_station_90days_expanded2.csv'
CAND = Path('network_candidates_deep.txt')

if not CAND.exists():
    print('network_candidates_deep.txt missing')
    raise SystemExit(1)

urls = [l.strip() for l in CAND.read_text(encoding='utf-8').splitlines() if l.strip() and l.startswith('http')]
interesting = [u for u in urls if any(k in u.lower() for k in ['.json','/wxinfo/','dyn_dat','one_json_uc','rain','isoh','/json/','/wxinfo','min','rhr','minds'])]
print('Found', len(interesting), 'interesting candidates')

# common date param variants
def make_variants(u, d):
    ymd = d.strftime('%Y%m%d')
    y_m_d = d.strftime('%Y-%m-%d')
    variants = [u,
                u + ('&' if '?' in u else '?') + 'date=' + ymd,
                u + ('&' if '?' in u else '?') + 'd=' + ymd,
                u + ('&' if '?' in u else '?') + 'time=' + ymd,
                u + ('&' if '?' in u else '?') + 'dt=' + ymd,
                u + ('&' if '?' in u else '?') + 'day=' + ymd,
                u + ('&' if '?' in u else '?') + 'date=' + y_m_d,
                u + ('&' if '?' in u else '?') + 'from=' + ymd + '&to=' + ymd,
                u + ('&' if '?' in u else '?') + 'start=' + ymd + '&end=' + ymd]
    return variants

DATE_RE = re.compile(r'20\d{2}-\d{2}-\d{2}|\d{8}')

def try_parse_json(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None


def try_date_str(s):
    if not s:
        return None
    s = str(s)
    if re.match(r'^\d{8}$', s):
        try:
            return datetime.strptime(s[:8], '%Y%m%d').date()
        except Exception:
            return None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        try:
            return datetime.strptime(s[:10], '%Y-%m-%d').date()
        except Exception:
            return None
    m = re.search(r'(20\d{6})', s)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y%m%d').date()
        except Exception:
            return None
    return None


def extract_timeseries_from_obj(obj):
    rows = []
    def walk(o):
        if isinstance(o, dict):
            keys = list(o.keys())[:24]
            # date-keyed dict
            if keys and any(isinstance(k, str) and DATE_RE.search(k) for k in keys):
                for k,v in o.items():
                    dt = try_date_str(k)
                    if not dt:
                        continue
                    if isinstance(v, dict):
                        for st,val in v.items():
                            try:
                                valn = float(val)
                            except Exception:
                                continue
                            rows.append({'date': dt, 'station': str(st).strip(), 'value': valn})
                    else:
                        try:
                            valn = float(v)
                        except Exception:
                            continue
                        rows.append({'date': dt, 'station': 'site', 'value': valn})
                return
            # station-keyed dict? keys look like station ids
            if keys and any(re.match(r'^[A-Za-z0-9_\-]{2,}$', str(k)) for k in keys) and any(isinstance(v,(int,float,str)) for v in list(o.values())[:6]):
                # try treating as station->date or station->value
                for k,v in o.items():
                    if isinstance(v, dict):
                        for subk,subv in v.items():
                            dt = try_date_str(subk)
                            if not dt:
                                continue
                            try:
                                valn = float(subv)
                            except Exception:
                                continue
                            rows.append({'date': dt, 'station': str(k).strip(), 'value': valn})
                        continue
                    # else try numeric
                    try:
                        valn = float(v)
                        rows.append({'date': date.today(), 'station': str(k).strip(), 'value': valn})
                    except Exception:
                        pass
                # don't return — continue deeper
            for vv in o.values():
                walk(vv)
        elif isinstance(o, list):
            if not o:
                return
            if isinstance(o[0], dict):
                sample = o[0]
                date_key = None
                val_key = None
                for kk in sample.keys():
                    if 'date' in kk.lower() or DATE_RE.search(str(kk)):
                        date_key = kk
                        break
                for kk in sample.keys():
                    if kk == date_key:
                        continue
                    sv = sample.get(kk)
                    if isinstance(sv,(int,float)) or (isinstance(sv,str) and re.match(r'^[0-9.+-]', str(sv))):
                        val_key = kk
                        break
                if date_key and val_key:
                    for rec in o:
                        d = try_date_str(rec.get(date_key))
                        if not d:
                            continue
                        st = rec.get('station') or rec.get('site') or rec.get('station_id') or rec.get('id') or rec.get('name') or 'site'
                        try:
                            v = float(rec.get(val_key,0))
                        except Exception:
                            continue
                        rows.append({'date': d, 'station': str(st).strip(), 'value': v})
                    return
            for it in o:
                walk(it)
    walk(obj)
    return rows


def run_probe():
    today = date.today()
    all_rows = []
    detected = set()
    for u in interesting:
        # try daily sample for last 30 days first to detect usability
        usable = False
        for i in range(30):
            d = today - timedelta(days=i)
            for v in make_variants(u,d):
                try:
                    r = requests.get(v, timeout=8)
                except Exception:
                    continue
                j = try_parse_json(r.text)
                if j is None:
                    m = re.search(r'\{\s*"FLW".*', r.text, re.S)
                    if m:
                        try:
                            j = json.loads(m.group(0))
                        except Exception:
                            j = None
                if j is not None:
                    rows = extract_timeseries_from_obj(j)
                    if rows:
                        usable = True
                        detected.add(u)
                        break
            if usable:
                break
    print('Detected endpoints:', len(detected))
    # collect full 90 days for detected endpoints
    for u in detected:
        print('Collecting for', u)
        for i in range(90):
            d = today - timedelta(days=i)
            for v in make_variants(u,d):
                try:
                    r = requests.get(v, timeout=10)
                except Exception:
                    continue
                j = try_parse_json(r.text)
                if j is None:
                    m = re.search(r'\{\s*"FLW".*', r.text, re.S)
                    if m:
                        try:
                            j = json.loads(m.group(0))
                        except Exception:
                            j = None
                if j is not None:
                    rows = extract_timeseries_from_obj(j)
                    if rows:
                        all_rows.extend(rows)
                        break
            time.sleep(0.06)
    print('Collected raw rows:', len(all_rows))
    if not all_rows:
        print('No rows collected')
        return
    df = pd.DataFrame(all_rows)
    # normalize date and station
    df['date'] = pd.to_datetime(df['date']).dt.date
    df['station'] = df['station'].astype(str)
    pivot = df.pivot_table(index='date', columns='station', values='value', aggfunc='sum', fill_value=0)
    pivot = pivot.sort_index(ascending=True)
    pivot.to_csv(OUT_CSV2)
    print('Wrote', OUT_CSV2, 'shape', pivot.shape)
    # copy to renderer input
    target = ROOT / 'rain_by_station_90days.csv'
    target.write_text(OUT_CSV2.read_text(encoding='utf-8'), encoding='utf-8')
    # run renderer
    import subprocess
    print('Rendering animation...')
    subprocess.run([str(Path('/Users/liyuwen/pfad/.venv/bin/python')), str(ROOT / 'merge_and_render_rain.py')], check=True)

if __name__ == '__main__':
    run_probe()
