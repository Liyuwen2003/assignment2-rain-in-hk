# 🎮 SD5913 - Programming for Art and Design 🎨

Welcome to the repository for SD5913! This repo contains weekly exercises, projects, and examples for the Programming for Artists and Designers class.

## 📂 Repository Structure

The repository is organized by weeks, with each folder containing the code and resources for that week's topics:

```
/week01, /week02, ... - Weekly content and exercises
/extra              - Additional code examples and resources
```

## 🚀 Getting Started

Clone the repo:
```bash
git clone https://github.com/venetanji/pfad
```

Update the repo:
```bash
git pull
```

Install requirements for a specific week:
```bash
cd pfad/week##/
pip install -r requirements.txt
```

## 📅 Weekly Content

### Week 01: Web Scraping & Data Collection 🕸️

In Week 01, we explore the basics of web scraping using Python. The main script connects to the Hong Kong Observatory website to fetch tide data. Key concepts covered include:

- Loading environment variables with `python-dotenv`
- Making HTTP requests with the `requests` library
## Hong Kong Rainfall — One-month visualization

This repository now contains a focused one-month visualization of rainfall across Hong Kong stations. The animation uses a raindrop-ripple metaphor where each station produces concentric ripples proportional to daily rainfall totals.

Contents of interest

- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.mp4` — High-resolution MP4 (1600×1600) for playback and sharing.
- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.webm` — WebM (VP9) version with better compression for web.
- `hong_kong_rainfall_1month/assignment2-for-visualization/` — Rendering scripts, CSV pivot (`rain_by_station_90days.csv`) and helper tools used to generate the animation.

Quick view

Start a local static server from the repository root and open the preview page:

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# open in a browser:
# http://localhost:8000/hong_kong_rainfall_1month/assignment2-for-visualization/view_animation_fast.html
```

Or open the MP4/WebM directly in your browser or media player.

Regenerating the animation

Recommended: use a Python virtual environment and install dependencies listed in `hong_kong_rainfall_1month/assignment2-for-visualization/requirements.txt`.

Fast preview:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r hong_kong_rainfall_1month/assignment2-for-visualization/requirements.txt
python generate_labeled_preview.py
```

Full render (smooth multi-frame-per-day ripples):

```bash
source .venv/bin/activate
python hong_kong_rainfall_1month/assignment2-for-visualization/render_fast_custom.py
```

Notes about large files

- GIF files can exceed 100 MB. GitHub rejects files larger than 100 MB and suggests using Git LFS for large binaries.
- To store the GIF in the repo use Git LFS locally:

```bash
brew install git-lfs         # macOS
git lfs install
echo "hong_kong_rainfall_1month/assignment2-for-visualization/*.gif filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
git add .gitattributes
git add hong_kong_rainfall_1month/assignment2-for-visualization/*.gif
git commit -m "Add large GIF via Git LFS"
git push <your-remote> main
```

Alternative: upload the large GIF as a GitHub Release asset (recommended for a single big file).

Next steps I can help with

- Add the large GIF to the repo via Git LFS (I'll prepare .gitattributes and instructions),
- Re-encode/convert the GIF to a smaller WebM to include in the repo,
- Tweak labels, fonts, or which stations are shown.

Last updated: 2025-09-28

