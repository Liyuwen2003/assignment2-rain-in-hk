
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

def fetch_visibility_timeseries(url):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(8)

    # 尝试抓取表格数据
    tables = driver.find_elements(By.TAG_NAME, 'table')
    print(f"Chrome: 网页中找到 {len(tables)} 个表格")
    data = []
    for table in tables:
        rows = table.find_elements(By.TAG_NAME, 'tr')
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, 'td')
            # 典型格式：时间、能见度
            if len(cols) >= 2:
                time_str = cols[0].text.strip()
                vis_str = cols[1].text.strip()
                try:
                    vis_val = float(vis_str.replace('米','').replace('m','').replace('M','').replace('公里','').replace('km','').replace('KM',''))
                    data.append((time_str, vis_val))
                except ValueError:
                    continue
    driver.quit()
    print(f"Chrome: 成功解析到 {len(data)} 条能见度时序数据")
    return data

import requests
from lxml import html
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def fetch_transparency_data(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding
    tree = html.fromstring(response.text)
    # 调试输出，查看表格数量
    tables = tree.xpath('//table')
    print(f"网页中找到 {len(tables)} 个表格")
    if not tables:
        print("未找到任何表格，请检查网页结构！")
        return []
    table = tables[0]
    rows = table.xpath('.//tr')
    print(f"表格中找到 {len(rows)} 行")
    if len(rows) <= 1:
        print("表格行数异常，可能网页结构已变！")
        return []
    data = []
    for row in rows[1:]:  # 跳过表头
        cols = row.xpath('.//td')
        print(f"当前行有 {len(cols)} 列")
        if len(cols) >= 3:
            region = cols[0].text_content().strip()
            transparency = cols[2].text_content().strip()
            try:
                transparency_val = float(transparency)
                data.append((region, transparency_val))
            except ValueError:
                print(f"透明度数据无法转换为数字: {transparency}")
                continue
    print(f"成功解析到 {len(data)} 条区域透明度数据")
    print(data)
    return data

def plot_transparency(data):
    regions = [d[0] for d in data]
    values = [d[1] for d in data]
    norm = mcolors.Normalize(vmin=min(values), vmax=max(values))
    cmap = plt.get_cmap('Blues')
    colors = [cmap(norm(v)) for v in values]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(regions, values, color=colors)
    plt.xlabel('区域')
    plt.ylabel('透明度 (米)')
    plt.title('香港各水域透明度分布（蓝色越深水质越好）')
    plt.xticks(rotation=45, ha='right')
    plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), label='透明度')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    url = "https://www.hko.gov.hk/tc/wxinfo/ts/hka_vis_past_ts.htm"
    try:
        data = fetch_visibility_timeseries(url)
        if data:
            import matplotlib.pyplot as plt
            times = [d[0] for d in data]
            values = [d[1] for d in data]
            plt.figure(figsize=(12,6))
            plt.plot(times, values, marker='o', color='blue')
            plt.xlabel('时间')
            plt.ylabel('能见度（米/公里）')
            plt.title('赤鱲角过去时序能见度')
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        else:
            print("Chrome 未能获取赤鱲角能见度数据，请检查网页结构或网络连接。")
    except Exception as e:
        print(f"Chrome 抓取或可视化失败: {e}")
