"""Deep network inspection and ripple visualization using real time-series when found.

Steps:
- Use Selenium (performance logs) to capture network calls with longer waits and simulated clicks.
- Save candidate URLs to network_candidates_deep.txt.
- Try to fetch each candidate and detect JSON time-series (date+value per station).
- If time-series found, compute 90-day totals per station and generate `ripple_total.png`.
"""
from __future__ import annotations

import json
import re
import time
from typing import List, Dict

import requests
import datetime
import math
import hashlib
import random

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    SEL = True
except Exception:
    SEL = False


def capture_network_deep(url: str, wait_seconds: int = 15, max_clicks: int = 20) -> List[str]:
    urls = set()
    if not SEL:
        print('Selenium not available; cannot deep inspect')
        return []

    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(url)
        time.sleep(wait_seconds)

        def collect():
            logs = driver.get_log('performance')
            for entry in logs:
                try:
                    msg = json.loads(entry['message'])['message']
                except Exception:
                    continue
                method = msg.get('method')
                params = msg.get('params', {})
                if method == 'Network.requestWillBeSent':
                    req = params.get('request', {})
                    u = req.get('url')
                    if u:
                        urls.add(u)
                elif method == 'Network.responseReceived':
                    resp = params.get('response', {})
                    u = resp.get('url')
                    if u:
                        urls.add(u)

        collect()

        # find clickable elements to try to trigger AJAX
        candidates = driver.find_elements(By.XPATH, "//a|//button|//input[@type='button']|//input[@type='submit']|//select")
        clicks = 0
        for el in candidates:
            if clicks >= max_clicks:
                break
            try:
                # only visible
                if not el.is_displayed():
                    continue
                # try to click via JS to avoid new tab
                driver.execute_script('arguments[0].scrollIntoView(true);', el)
                time.sleep(0.2)
                try:
                    el.click()
                except Exception:
                    driver.execute_script('arguments[0].click();', el)
                time.sleep(1.2)
                collect()
                clicks += 1
            except Exception:
                continue

        # also try some programmatic interactions: change selects
        selects = driver.find_elements(By.TAG_NAME, 'select')
        for s in selects[:5]:
            try:
                opts_el = s.find_elements(By.TAG_NAME, 'option')
                for o in opts_el[:4]:
                    try:
                        driver.execute_script('arguments[0].selected = true; arguments[0].dispatchEvent(new Event("change"));', o)
                        time.sleep(1.0)
                        collect()
                    except Exception:
                        continue
            except Exception:
                continue

        # final wait & collect
        time.sleep(2)
        collect()

        urls_list = sorted(urls)
        with open('network_candidates_deep.txt', 'w', encoding='utf-8') as f:
            for u in urls_list:
                f.write(u + '\n')

        print('Deep capture saved', len(urls_list), 'urls to network_candidates_deep.txt')
        return urls_list
    finally:
        driver.quit()


def is_json_like_url(u: str) -> bool:
    return any(x in u.lower() for x in ['.json', 'api', 'data', 'wxinfo', 'json', 'dyn'])


date_re = re.compile(r'20\d{2}[-/]?\d{2}[-/]?\d{2}|\d{4}-\d{2}-\d{2}|\d{8}')


def find_timeseries_in_obj(obj, path=''):
    results = []
    # If list of dicts with date-like key
    if isinstance(obj, list) and len(obj) >= 3 and all(isinstance(i, dict) for i in obj[:min(10, len(obj))]):
        # try to find date-like and numeric key
        sample = obj[0]
        date_key = None
        value_key = None
        for k in sample.keys():
            if date_re.search(k) or 'date' in k.lower() or 'time' in k.lower():
                date_key = k
        # find numeric key
        for k in sample.keys():
            v = sample.get(k)
            if isinstance(v, (int, float)) or (isinstance(v, str) and re.match(r'^[0-9.+-]', v.strip())):
                if k != date_key:
                    value_key = k
                    break
        if date_key and value_key:
            results.append({'path': path, 'type': 'list_of_dicts', 'date_key': date_key, 'value_key': value_key})

    if isinstance(obj, dict):
        # if mapping of station-> {date:value} or station->{records}
        # check if values are lists/dicts that look like timeseries
        for k, v in obj.items():
            if isinstance(v, dict):
                # keys may be date strings
                if any(date_re.search(str(kk)) for kk in list(v.keys())[:50]):
                    # pick numeric sample
                    results.append({'path': path + '/' + k, 'type': 'dict_date_map'})
            if isinstance(v, list):
                sub = find_timeseries_in_obj(v, path + '/' + k)
                results.extend(sub)

    return results


def analyze_candidates(urls: List[str]):
    found_times = []
    for u in urls:
        if u.startswith('data:'):
            continue
        try:
            r = requests.get(u, timeout=15)
        except Exception:
            continue
        ct = r.headers.get('Content-Type','')
        txt = r.text
        if txt.strip().startswith('{') or txt.strip().startswith('['):
            try:
                j = r.json()
            except Exception:
                continue
            res = find_timeseries_in_obj(j)
            if res:
                print('Timeseries-like structures in', u)
                for x in res:
                    print(' ', x)
                found_times.append((u, res))
        else:
            # try xml
            if txt.strip().startswith('<'):
                if 'rain' in txt.lower() or date_re.search(txt):
                    print('XML contains rain/date-like in', u)
    return found_times


def compute_totals_from_json_url(u: str):
    # Try to fetch and compute per-station totals for last 90 days using naive heuristics
    try:
        r = requests.get(u, timeout=15)
        j = r.json()
    except Exception:
        return None

    # Look for structures: list of dicts with date and station values, or dict of stations -> {date:val}
    candidates = []
    def walk(o, path=''):
        if isinstance(o, list):
            if len(o) >= 3 and isinstance(o[0], dict):
                candidates.append((path, o))
            for i, it in enumerate(o[:10]):
                walk(it, f'{path}[{i}]')
        elif isinstance(o, dict):
            # dict with date-like keys
            if any(date_re.search(k) for k in list(o.keys())[:200]):
                candidates.append((path, o))
            for k, v in list(o.items())[:200]:
                walk(v, path + '/' + k)

    walk(j)
    # Heuristic: find candidate with date keys mapping to numbers or station keys mapping to dicts
    totals = {}
    for path, obj in candidates:
        if isinstance(obj, dict):
            # date-> station mapping or date->value
            # try parse date keys
            for dk, dv in obj.items():
                if not date_re.search(dk):
                    continue
                # if dv is dict of stations
                if isinstance(dv, dict):
                    for st, val in dv.items():
                        try:
                            valn = float(val)
                        except Exception:
                            continue
                        totals[st] = totals.get(st, 0.0) + valn
                else:
                    # single value; aggregate to 'global'
                    try:
                        v = float(dv)
                        totals['total'] = totals.get('total', 0.0) + v
                    except Exception:
                        continue
        elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
            # list of records with date and station/value keys
            # find date key and numeric key
            sample = obj[0]
            dkey = None
            vkey = None
            for k in sample.keys():
                if date_re.search(k) or 'date' in k.lower() or 'time' in k.lower():
                    dkey = k
            for k in sample.keys():
                if k != dkey:
                    if isinstance(sample[k], (int, float)) or (isinstance(sample[k], str) and re.match(r'^\s*[0-9.+-]', sample[k])):
                        vkey = k
                        break
            if dkey and vkey:
                for rec in obj:
                    try:
                        val = float(rec.get(vkey, 0))
                    except Exception:
                        continue
                    st = rec.get('station') or rec.get('site') or rec.get('station_id') or 'site'
                    totals[st] = totals.get(st, 0.0) + val

    return totals if totals else None


def make_ripple_from_totals(totals: Dict[str, float], outpath='ripple_total.png'):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle

    if not totals:
        print('No totals to visualize')
        return

    items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:200]
    vals = [v for k, v in items]
    vmin = min(vals)
    vmax = max(vals)
    norm = lambda x: 0.0 + 1.0 * ((x - vmin) / (vmax - vmin) if vmax > vmin else 0.5)

    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    ax.set_facecolor('#f7fcff')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    random.seed(123)
    for key, val in items:
        t = norm(val)
        # position from hash
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

    ax.set_title('90-day rainfall totals — ripple visualization', fontsize=14)
    plt.tight_layout()
    fig.savefig(outpath)
    print('Wrote ripple totals to', outpath)


def main():
    url = 'https://my.weather.gov.hk/tc/wxinfo/rainfall/isohyet_daily.shtml'
    urls = capture_network_deep(url, wait_seconds=18, max_clicks=30)
    found = analyze_candidates(urls)
    totals = None
    # try to compute totals from any candidate
    for u, _ in found:
        t = compute_totals_from_json_url(u)
        if t:
            totals = t
            print('Computed totals from', u)
            break

    # fallback: try scanning all captured URLs for JSON-like
    if totals is None:
        for u in urls:
            if is_json_like_url(u):
                t = compute_totals_from_json_url(u)
                if t:
                    totals = t
                    print('Computed totals from', u)
                    break

    if totals:
        make_ripple_from_totals(totals, outpath='ripple_total.png')
    else:
        print('No time-series totals found from captured endpoints.')


if __name__ == '__main__':
    main()
