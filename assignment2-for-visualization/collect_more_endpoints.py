"""Probe captured network candidates and collect per-station daily rainfall from multiple endpoints.

Strategy:
- Read `network_candidates_deep.txt`, filter likely data endpoints (json, wxinfo, DYN_DAT, one_json_uc, rainfall).
- For each candidate try a small sample of dates (every 7 days over last 90 days) with common date query patterns.
- If an endpoint yields per-station/date structured data, fetch full 90 days and aggregate into CSV.

Outputs:
- assignment2-for-visualization/rain_by_station_90days_expanded.csv
- assignment2-for-visualization/expanded_endpoints_log.txt
"""
from pathlib import Path
import requests, json, re
from datetime import date, timedelta, datetime
import time
import pandas as pd

ROOT = Path('assignment2-for-visualization')
ROOT.mkdir(exist_ok=True)
OUT_CSV = ROOT / 'rain_by_station_90days_expanded.csv'
LOG = ROOT / 'expanded_endpoints_log.txt'

cand_file = Path('network_candidates_deep.txt')
if not cand_file.exists():
    print('network_candidates_deep.txt not found')
    raise SystemExit(1)

urls = [l.strip() for l in cand_file.read_text(encoding='utf-8').splitlines() if l.strip() and l.startswith('http')]
interesting = [u for u in urls if any(k in u.lower() for k in ['.json','/wxinfo/','dyn_dat','one_json_uc','rain','isoh','/json/','/wxinfo'])]
print('Found', len(interesting), 'interesting candidates')

DATE_RE = re.compile(r'20\d{2}-\d{2}-\d{2}|\d{8}')

def try_parse_json(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None

def extract_timeseries_from_obj(obj):
    # Look for patterns: date-keyed dicts (YYYYMMDD or YYYY-MM-DD) mapping to station->value
    # or list-of-records with explicit date and numeric value keys.
    rows = []

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
        # maybe contains YYYYMMDD at start
        m = re.search(r'(20\d{6})', s)
        if m:
            try:
                return datetime.strptime(m.group(1), '%Y%m%d').date()
            except Exception:
                return None
        return None

    def walk(obj):
        if isinstance(obj, dict):
            # quick check: are many keys date-like?
            keys = list(obj.keys())[:12]
            if keys and any(isinstance(k, str) and DATE_RE.search(k) for k in keys):
                # attempt to treat as date->station_map dict
                for k, v in obj.items():
                    dt = try_date_str(k)
                    if not dt:
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
                        except Exception:
                            continue
                        rows.append({'date': dt, 'station': 'value', 'value': valn})
                return
            # otherwise recurse
            for v in obj.values():
                walk(v)

        elif isinstance(obj, list):
            if not obj:
                return
            if isinstance(obj[0], dict):
                # find candidate date and numeric keys
                sample = obj[0]
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
                    if isinstance(sv, (int, float)) or (isinstance(sv, str) and re.match(r'^[0-9.+-]', str(sv))):
                        val_key = kk
                        break
                if date_key and val_key:
                    for rec in obj:
                        try:
                            dstr = rec.get(date_key)
                            d = try_date_str(dstr)
                            if not d:
                                continue
                        except Exception:
                            continue
                        try:
                            v = float(rec.get(val_key, 0))
                        except Exception:
                            continue
                        st = rec.get('station') or rec.get('site') or rec.get('station_id') or rec.get('id') or rec.get('name') or 'site'
                        rows.append({'date': d, 'station': str(st), 'value': v})
                    return
            # otherwise recurse into list items
            for it in obj:
                walk(it)

    walk(obj)
    return rows


def probe_endpoint_sample(u, sample_dates):
    # try variants for each date; return True if any date yields rows
    for d in sample_dates:
        variants = [u, u + ('&' if '?' in u else '?') + 'date=' + d.strftime('%Y%m%d'), u + ('&' if '?' in u else '?') + 'd=' + d.strftime('%Y%m%d'), u + ('&' if '?' in u else '?') + 'time=' + d.strftime('%Y%m%d')]
        for v in variants:
            try:
                r = requests.get(v, timeout=8)
            except Exception:
                continue
            j = try_parse_json(r.text)
            if j is not None:
                rows = extract_timeseries_from_obj(j)
                if rows:
                    return True
            else:
                # xml may contain embedded json
                m = re.search(r'\{\s*"FLW".*', r.text, re.S)
                if m:
                    try:
                        j2 = json.loads(m.group(0))
                        rows = extract_timeseries_from_obj(j2)
                        if rows:
                            return True
                    except Exception:
                        pass
    return False


def collect_full_for_endpoint(u, days=90):
    rows = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        variants = [u + ('&' if '?' in u else '?') + 'date=' + d.strftime('%Y%m%d'), u + ('&' if '?' in u else '?') + 'd=' + d.strftime('%Y%m%d'), u + ('&' if '?' in u else '?') + 'time=' + d.strftime('%Y%m%d'), u]
        got = False
        for v in variants:
            try:
                r = requests.get(v, timeout=10)
            except Exception:
                continue
            j = try_parse_json(r.text)
            if j is not None:
                rr = extract_timeseries_from_obj(j)
                if rr:
                    rows.extend(rr)
                    got = True
                    break
            else:
                m = re.search(r'\{\s*"FLW".*', r.text, re.S)
                if m:
                    try:
                        j2 = json.loads(m.group(0))
                        rr = extract_timeseries_from_obj(j2)
                        if rr:
                            rows.extend(rr)
                            got = True
                            break
                    except Exception:
                        pass
        time.sleep(0.12)
    return rows


def main():
    today = date.today()
    sample_dates = [today - timedelta(days=i) for i in range(0,90,7)]
    detected = []
    for u in interesting:
        try:
            ok = probe_endpoint_sample(u, sample_dates)
            if ok:
                print('Detected data endpoint:', u)
                detected.append(u)
        except Exception as e:
            print('Probe error for', u, e)

    LOG.write_text('Detected endpoints:\n' + '\n'.join(detected), encoding='utf-8')
    all_rows = []
    for u in detected:
        print('Collecting full 90 days for', u)
        rr = collect_full_for_endpoint(u, days=90)
        print('  got rows', len(rr))
        all_rows.extend(rr)

    if not all_rows:
        print('No rows collected from detected endpoints')
        return

    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date']).dt.date
    pivot = df.pivot_table(index='date', columns='station', values='value', aggfunc='sum', fill_value=0)
    pivot = pivot.sort_index(ascending=True)
    pivot.to_csv(OUT_CSV)
    print('Wrote expanded CSV', OUT_CSV, 'shape', pivot.shape)


if __name__ == '__main__':
    main()
