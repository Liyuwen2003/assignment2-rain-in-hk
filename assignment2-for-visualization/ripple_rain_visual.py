"""Artistic ripple visualization for rainfall using HKO JSON/JS hints.

This script fetches `DYN_DAT_WARNSUM.json` and `section.js`, extracts a set
of site IDs and weights, and produces a layered ripple image where:
- number of ripples and radius are influenced by the site weight,
- color ranges from light-blue to deep-blue based on total weight,
- recent rain-warning issuance increases ripple frequency.

Output: `ripple_rain.png` saved to the same directory.
"""
from __future__ import annotations

import json
import math
import hashlib
import datetime
import random
from typing import Dict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import requests


def fetch_json(url: str):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.text


def parse_section_js(js_text: str) -> Dict[str, float]:
    # js_text looks like: var section = {"key":value, ...};
    start = js_text.find('{')
    end = js_text.rfind('}')
    if start == -1 or end == -1:
        return {}
    obj = js_text[start:end+1]
    # ensure valid JSON (keys in quotes already)
    try:
        return json.loads(obj)
    except Exception:
        # fall back: replace unquoted keys (unlikely) and eval cautiously
        return {}


def parse_warnsum(json_text: str) -> Dict[str, str]:
    try:
        j = json.loads(json_text)
        root = j.get('DYN_DAT_WARNSUM', {})
        return root
    except Exception:
        return {}


def key_to_xy(key: str, w: int = 1000):
    # Deterministic pseudo-random placement via hash
    h = hashlib.sha1(key.encode('utf-8')).hexdigest()
    a = int(h[:8], 16)
    b = int(h[8:16], 16)
    x = (a % w) / w
    y = (b % w) / w
    return x, y


def make_ripples(section_map: Dict[str, float], warnsum: Dict[str, str], outpath='ripple_rain.png'):
    # Prepare canvas
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    ax.set_facecolor('#f7fcff')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])

    # Build weights list
    items = list(section_map.items())[:250]  # limit to first 250 for performance/art
    keys = [k for k, v in items]
    vals = [float(v) for k, v in items]

    if not vals:
        raise RuntimeError('No section mapping found to visualize')

    # normalize weights to 0.1..1.0
    vmin = min(vals)
    vmax = max(vals)
    norm = lambda x: 0.1 + 0.9 * ((x - vmin) / (vmax - vmin) if vmax > vmin else 0.5)

    # rain-warning derived frequency factor (global heuristic)
    wf = 1
    w_c = warnsum.get('WRAIN_C', {}) if isinstance(warnsum.get('WRAIN_C', {}), dict) else {}
    issue_date = w_c.get('Issue_Date', '')
    try:
        if issue_date:
            dt = datetime.datetime.strptime(issue_date, '%Y%m%d')
            delta = (datetime.datetime.utcnow() - dt).days
            if delta <= 30:
                wf = 3
            elif delta <= 90:
                wf = 2
    except Exception:
        wf = 1

    random.seed(42)
    for key, raw in items:
        w = float(raw)
        weight = norm(w)
        x, y = key_to_xy(key)
        # jitter positions slightly for visual variety
        x = min(max(x + (random.random() - 0.5) * 0.02, 0.02), 0.98)
        y = min(max(y + (random.random() - 0.5) * 0.02, 0.02), 0.98)

        # number of ripples depends on weight and global wf
        n_ripples = max(2, int(1 + weight * 6) * wf)
        base_radius = 0.02 + 0.12 * weight
        spacing = 0.02 + 0.03 * (1 - weight)

        # color: interpolate from light to deep blue
        # light: #d7eefb  deep: #0b3d91
        def mix_color(t: float):
            # t in [0,1]
            c1 = (215, 238, 251)
            c2 = (11, 61, 145)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            return (r/255, g/255, b/255)

        col = mix_color(weight)

        for i in range(n_ripples):
            rads = base_radius + i * spacing * (1 + 0.08 * (random.random() - 0.5))
            alpha = max(0.02, math.exp(-0.6 * i) * weight * 0.9)
            circ = Circle((x, y), rads, linewidth=1.0, edgecolor=col, facecolor='none', alpha=alpha)
            ax.add_patch(circ)

    # overlay a subtle vignette or noise using translucent patches
    ax.set_title('Rain Ripples — HKO-derived artistic visualization', fontsize=14)
    plt.tight_layout()
    fig.savefig(outpath)
    print(f'Wrote visualization to {outpath}')


def main():
    try:
        sec_js = fetch_json('https://my.weather.gov.hk/js/data/section.js')
        sec_map = parse_section_js(sec_js)
    except Exception as e:
        print('Failed to fetch/parse section.js:', e)
        sec_map = {}

    try:
        warn_txt = fetch_json('https://my.weather.gov.hk/json/DYN_DAT_WARNSUM.json')
        warn_map = parse_warnsum(warn_txt)
    except Exception as e:
        print('Failed to fetch/parse DYN_DAT_WARNSUM.json:', e)
        warn_map = {}

    if not sec_map:
        # fallback: generate synthetic sites
        print('No section mapping found; generating synthetic points')
        sec_map = {f'site{i}': (i % 7) + 1 for i in range(80)}

    make_ripples(sec_map, warn_map, outpath='ripple_rain.png')


if __name__ == '__main__':
    main()
