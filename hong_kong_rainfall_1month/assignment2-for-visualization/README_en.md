Hong Kong Rainfall by District — One-month visualization

Overview

- This animation visualizes approximately the last 30 days of rainfall across Hong Kong districts, collected from public meteorological sources.
- The visualization uses "raindrop ripple" graphics: each station is shown at a fixed position; larger rainfall produces stronger ripples.

Files

- hong_kong_rainfall_1month_1600.mp4 — High-resolution MP4 (1600×1600) suitable for playback and sharing.
- hong_kong_rainfall_1month_1600.gif — GIF fallback for environments without video support.

How to view

Run a simple local server from the repository root for best browser compatibility:

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# open in browser:
# http://localhost:8000/assignment2-for-visualization/view_animation_fast.html
```

You can also open the MP4 or GIF directly with your system player.

Options / next steps (I can do these for you)

- Export a WebM for smaller filesize and good browser support.
- Reduce label clutter by showing only the top-N stations.
- Overlay station positions on a map (requires lat/lon calibration).

Contact

Reply with any change requests (pacing, labels, formats) and I’ll update the files.
香港各区降水量 — 一个月可视化

内容说明

- 这是基于公开气象源抓取并汇总的香港各区近 30 天降水量的动态可视化。
- 可视化形式为“水滴涟漪”动画：每个测站按固定位置显示，雨量越大涟漪越明显。

文件列表

- 香港各区降水量_1月_1600.mp4 — 高清 MP4 视频（1600×1600），适合播放和下载。
- 香港各区降水量_1月_1600.gif — GIF 版本，便于在不支持视频的环境查看。

如何查看

建议在本地启动简单静态服务器以获得最佳浏览体验：

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# 浏览器打开： http://localhost:8000/assignment2-for-visualization/view_animation_fast.html
```

如果直接打开 MP4 或 GIF 文件，系统自带播放器也能播放（某些浏览器在 file:// 下可能限制控制显示）。

可选项（如需我代劳）

- 压缩为 WebM 以便分享（体积更小）。
- 调整标签数量、字体大小或只显示重点站名。
## Hong Kong Rainfall — One-month visualization

This folder contains a one-month raindrop-style visualization of rainfall across Hong Kong stations. The animation shows per-station ripple intensity driven by daily rainfall totals.

What you'll find

- `hong_kong_rainfall_1month_1600.mp4` — High-resolution MP4 (1600×1600). Good for playback and sharing.
- `hong_kong_rainfall_1month_1600.webm` — WebM (VP9) version with better compression for web.
- Supporting scripts and data in `assignment2-for-visualization/` (CSV pivot, rendering scripts).

View locally

1. Start a local static server from the repo root and open the preview HTML:

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# then open in a browser:
# http://localhost:8000/hong_kong_rainfall_1month/assignment2-for-visualization/view_animation_fast.html
```

2. Or open the MP4/WebM directly in your media player or browser.

How to regenerate the animation

Requirements (recommended): Python 3.10+, a virtual environment, and the packages listed in `assignment2-for-visualization/requirements.txt`.

Basic steps (fast preview):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r assignment2-for-visualization/requirements.txt
python generate_labeled_preview.py    # creates the labeled preview MP4/WebM in this folder
```

For full re-rendering from the CSV pivot (multi-frame-per-day smooth ripples):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r assignment2-for-visualization/requirements.txt
python assignment2-for-visualization/render_fast_custom.py
```

Large GIFs and distribution notes

- The original GIF can be very large (>100 MB). GitHub rejects files larger than 100 MB and recommends Git LFS for large binaries.
- If you want the GIF in this repository, use Git LFS locally:

```bash
# install git-lfs (macOS with Homebrew)
brew install git-lfs
git lfs install
# mark the gif path and re-commit
echo "hong_kong_rainfall_1month/assignment2-for-visualization/*.gif filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
git add .gitattributes
git add hong_kong_rainfall_1month/assignment2-for-visualization/*.gif
git commit -m "Add large GIF via Git LFS"
git push origin main
```

Alternative: upload the large GIF as a GitHub Release asset (recommended for single large files).

Contact / next steps

Tell me which of the following you prefer and I'll follow up:
- Add the large GIF to the repo using Git LFS (I can prepare the .gitattributes and push if you enable LFS locally),
- Compress/convert the GIF to a smaller WebM and add it to the repo,
- Create a GitHub Release and upload the large GIF as an asset (I can prepare the release notes), or
- Make further visual tweaks (labeling, colors, per-station thresholds).

Last updated: 2025-09-28
