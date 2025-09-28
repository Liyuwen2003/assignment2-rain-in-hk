"""
visualize_weather.py

Starter template for fetching and visualizing weather/visibility time series.
Placeholders are provided for data fetching, parsing and plotting.

How to use:
- Fill fetch_data() to return a list of (datetime, value) tuples or a pandas DataFrame.
- Run locally with:
    python visualize_weather.py --help

Optional runtime (recommended): create a virtualenv and install matplotlib/pandas/requests.
"""

from __future__ import annotations

import argparse
import datetime
import re
from typing import List, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import requests
from lxml import html
import json

# Optional imports
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

# Selenium fallback only if needed
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False


def fetch_data(source: str) -> List[Tuple[datetime.datetime, float]]:
    """Fetch time-series weather data from `source`.

    Args:
        source: URL or local path. Implement fetching/parsing here.

    Returns:
        List of (datetime, value) pairs. Value should be a numeric (e.g., visibility in km).
    """
    # If source is empty, use the HKO rainfall isohyet daily page
    if not source:
        source = "https://my.weather.gov.hk/tc/wxinfo/rainfall/isohyet_daily.shtml"

    # Try requests first
    try:
        resp = requests.get(source, timeout=15)
        resp.encoding = resp.apparent_encoding
        page = resp.text
        tables = parse_rainfall_tables(page)
        if tables is not None and not tables.empty:
            return _df_to_timeseries(tables)
    except Exception as e:
        print(f"requests fetch failed: {e}")

    # Fallback to Selenium if available
    if SELENIUM_AVAILABLE:
        print("Falling back to Selenium for dynamic content...")
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(source)
            # wait a bit for JS to render
            import time

            time.sleep(6)
            page = driver.page_source
            driver.quit()
            tables = parse_rainfall_tables(page)
            if tables is not None and not tables.empty:
                return _df_to_timeseries(tables)
        except Exception as e:
            print(f"selenium fetch failed: {e}")

    # If everything fails, return empty
    return []


def parse_rainfall_tables(page_html: str) -> pd.DataFrame:
    """Attempt to parse HTML and return a DataFrame in long format:
    index: date (datetime), columns: station names (or a multi-station long table)
    Heuristic parser: find tables where first column looks like a date.
    """
    tree = html.fromstring(page_html)
    tables = tree.xpath('//table')
    parsed_frames = []
    date_pattern = re.compile(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}")

    for table in tables:
        rows = table.xpath('.//tr')
        if not rows:
            continue
        # Extract header
        header_cells = rows[0].xpath('.//th|.//td')
        headers = [c.text_content().strip() for c in header_cells]
        # If headers are empty or only one cell, try to use first row values as header
        data_rows = []
        for r in rows[1:]:
            cols = r.xpath('.//td')
            texts = [c.text_content().strip() for c in cols]
            if not texts:
                continue
            # Check whether first column looks like date
            if date_pattern.search(texts[0]):
                data_rows.append(texts)
        if data_rows:
            # Build DataFrame
            try:
                df = pd.DataFrame(data_rows)
                # If headers length matches columns, set them
                if len(headers) == df.shape[1]:
                    df.columns = headers
                # Try to coerce first column to datetime
                df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
                if df.iloc[:, 0].notna().sum() > 0:
                    parsed_frames.append(df)
            except Exception:
                continue

    if not parsed_frames:
        return pd.DataFrame()

    # Prefer the largest frame (most rows)
    parsed_frames.sort(key=lambda x: x.shape[0], reverse=True)
    return parsed_frames[0]


def _df_to_timeseries(df: pd.DataFrame) -> List[Tuple[datetime.datetime, float]]:
    """Convert parsed DataFrame to a single station timeseries if possible.
    If multiple stations present, aggregate or pick a default station.
    For this starter template, we will pick the first numeric column after the date column.
    """
    if df.empty:
        return []
    # Find first numeric column (after date)
    for col in df.columns[1:]:
        # try to coerce to numeric
        numeric = pd.to_numeric(df[col].str.replace('[^0-9.-]', '', regex=True), errors='coerce')
        if numeric.notna().sum() > 0:
            series = list(zip(pd.to_datetime(df.iloc[:, 0]).tolist(), numeric.tolist()))
            # filter NaN
            series = [(d, v) for d, v in series if pd.notna(v) and d is not pd.NaT]
            return series
    return []


def inspect_network_calls(url: str, wait_seconds: int = 8) -> List[str]:
    """Use Chrome performance logs to capture network requests and return candidate JSON endpoints.

    Returns a list of unique URLs that look like JSON endpoints.
    """
    if not SELENIUM_AVAILABLE:
        print("Selenium not available. Install selenium to use network inspection.")
        return []

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    # enable performance logging
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        import time

        time.sleep(wait_seconds)

        # fetch performance logs
        logs = driver.get_log('performance')
        urls = set()
        for entry in logs:
            try:
                message = json.loads(entry['message'])['message']
            except Exception:
                continue
            method = message.get('method')
            params = message.get('params', {})
            # Look for requests and responses
            if method == 'Network.requestWillBeSent':
                req = params.get('request', {})
                url_req = req.get('url')
                if url_req and (url_req.endswith('.json') or 'api' in url_req or 'data' in url_req or 'json' in url_req):
                    urls.add(url_req)
            elif method == 'Network.responseReceived':
                resp = params.get('response', {})
                mime = resp.get('mimeType', '')
                url_resp = resp.get('url')
                if url_resp and ('json' in mime or url_resp.endswith('.json') or 'api' in url_resp):
                    urls.add(url_resp)

        urls_list = sorted(urls)
        # save to file for inspection
        with open('network_candidates.txt', 'w', encoding='utf-8') as f:
            for u in urls_list:
                f.write(u + '\n')

        print(f"Captured {len(urls_list)} candidate endpoints; saved to network_candidates.txt")
        return urls_list
    finally:
        driver.quit()


def plot_timeseries(timeseries: List[Tuple[datetime.datetime, float]], title: str = "Visibility") -> None:
    """Simple time-series plot helper.

    Args:
        timeseries: list of (datetime, value)
        title: plot title
    """
    if not timeseries:
        print("No data to plot.")
        return

    times, values = zip(*timeseries)

    plt.figure(figsize=(10, 5))
    plt.plot(times, values, marker="o", color="tab:blue")
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Value")
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weather / visibility visualization starter")
    p.add_argument("--source", "-s", help="Data source (URL or file)", default="")
    p.add_argument("--title", "-t", help="Plot title", default="Visibility Time Series")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    data = fetch_data(args.source)
    plot_timeseries(data, title=args.title)


if __name__ == "__main__":
    main()
