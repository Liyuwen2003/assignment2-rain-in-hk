"""Debug collection: probe candidates, collect raw extracted rows and summarize station names.
Writes: assignment2-for-visualization/expanded_raw_rows.jsonl
"""
from pathlib import Path
import requests, json, re
from datetime import date, timedelta, datetime
import time

ROOT = Path('assignment2-for-visualization')
CAND = Path('network_candidates_deep.txt')
OUT_RAW = ROOT / 'expanded_raw_rows.jsonl'

if not CAND.exists():
    print('network_candidates_deep.txt missing')
    raise SystemExit(1)

urls = [l.strip() for l in CAND.read_text(encoding='utf-8').splitlines() if l.strip() and l.startswith('http')]
interesting = [u for u in urls if any(k in u.lower() for k in ['.json','/wxinfo/','dyn_dat','one_json_uc','rain','isoh','/json/','/wxinfo'])]
print('Found', len(interesting), 'interesting candidates')

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
            # date-key dict?
            keys = list(o.keys())[:12]
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
                            rows.append({'date': str(dt), 'station': str(st).strip(), 'value': valn})
                    else:
                        try:
                            valn = float(v)
                        except Exception:
                            continue
                        # unknown station name, use endpoint-unknown
                        rows.append({'date': str(dt), 'station': 'unknown', 'value': valn})
                return
            # recurse
            for vv in o.values():
                walk(vv)
        elif isinstance(o, list):
            for it in o:
                if isinstance(it, dict):
                    # try to find date and numeric
                    date_key = None
                    val_key = None
                    for kk in it.keys():
                        if 'date' in kk.lower() or DATE_RE.search(str(kk)):
                            date_key = kk
                            break
                    for kk in it.keys():
                        if kk == date_key:
                            continue
                        sv = it.get(kk)
                        if isinstance(sv, (int,float)) or (isinstance(sv,str) and re.match(r'^[0-9.+-]', str(sv))):
                            val_key = kk
                            break
                    if date_key and val_key:
                        d = try_date_str(it.get(date_key))
                        if not d:
                            continue
                        st = it.get('station') or it.get('site') or it.get('station_id') or it.get('id') or it.get('name') or 'site'
                        try:
                            v = float(it.get(val_key, 0))
                        except Exception:
                            continue
                        rows.append({'date': str(d), 'station': str(st).strip(), 'value': v})
                    else:
                        # recurse inside
                        walk(it)
                else:
                    # skip non-dict list items
                    pass
    walk(obj)
    return rows


def probe_and_collect():
    today = date.today()
    sample_dates = [today - timedelta(days=i) for i in range(0,90,7)]
    detected = []
    for u in interesting:
        # probe
        ok = False
        for d in sample_dates:
            variants = [u, u + ('&' if '?' in u else '?') + 'date=' + d.strftime('%Y%m%d')]
            for v in variants:
                try:
                    r = requests.get(v, timeout=8)
                except Exception:
                    continue
                j = try_parse_json(r.text)
                if j is not None:
                    rs = extract_timeseries_from_obj(j)
                    if rs:
                        ok = True
                        break
        if ok:
            print('Detected', u)
            detected.append(u)
    if not detected:
        print('No detected endpoints')
        return
    all_rows = []
    with OUT_RAW.open('w', encoding='utf-8') as fh:
        for u in detected:
            print('Collecting', u)
            for i in range(90):
                d = today - timedelta(days=i)
                v = u + ('&' if '?' in u else '?') + 'date=' + d.strftime('%Y%m%d')
                try:
                    r = requests.get(v, timeout=10)
                except Exception:
                    continue
                j = try_parse_json(r.text)
                if j is None:
                    # try embedded json
                    m = re.search(r'\{\s*"FLW".*', r.text, re.S)
                    if m:
                        try:
                            j = json.loads(m.group(0))
                        except Exception:
                            j = None
                if j is not None:
                    rs = extract_timeseries_from_obj(j)
                    for row in rs:
                        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
                        all_rows.append(row)
                time.sleep(0.08)
    # summary
    stations = {}
    for r in all_rows:
        stations[r['station']] = stations.get(r['station'], 0) + 1
    print('Collected rows:', len(all_rows))
    print('Stations found:', len(stations))
    for k,v in sorted(stations.items(), key=lambda x:-x[1])[:30]:
        print(k, v)

if __name__ == '__main__':
    probe_and_collect()
