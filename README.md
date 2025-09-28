# Hong Kong Rainfall — One-month visualization

This repository contains a one-month raindrop-style visualization of rainfall across Hong Kong stations. The animation shows per-station ripple intensity driven by daily rainfall totals collected from public meteorological sources.

What you'll find

- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.mp4` — High-resolution MP4 (1600×1600) for playback and sharing.
- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.webm` — WebM (VP9) version with better compression for web.
- Supporting scripts and data in `hong_kong_rainfall_1month/assignment2-for-visualization/` (CSV pivot, rendering scripts).

View locally

Start a local static server from the repository root and open the preview page:

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# then open in a browser:
# http://localhost:8000/hong_kong_rainfall_1month/assignment2-for-visualization/view_animation_fast.html
```

Or open the MP4/WebM directly in your browser or media player.

How to regenerate the animation

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

- GIFs exceeding 100 MB are rejected by GitHub; consider using Git LFS or upload the large GIF as a GitHub Release asset.

If you want me to add the large GIF to the repo using Git LFS, compress the animation to a smaller WebM, or include screenshots in this README, tell me which and I'll proceed.

Last updated: 2025-09-28
This repository contains a one-month raindrop-style visualization of rainfall across Hong Kong stations. The animation shows per-station ripple intensity driven by daily rainfall totals collected from public meteorological sources.

What you'll find

- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.mp4` — High-resolution MP4 (1600×1600) for playback and sharing.
- `hong_kong_rainfall_1month/assignment2-for-visualization/hong_kong_rainfall_1month_1600.webm` — WebM (VP9) version with better compression for web.
- Supporting scripts and data in `hong_kong_rainfall_1month/assignment2-for-visualization/` (CSV pivot, rendering scripts).

View locally

Start a local static server from the repository root and open the preview page:

```bash
cd /Users/liyuwen/pfad
python -m http.server 8000
# then open in a browser:
# http://localhost:8000/hong_kong_rainfall_1month/assignment2-for-visualization/view_animation_fast.html
```

Or open the MP4/WebM directly in your browser or media player.

How to regenerate the animation

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

- GIFs exceeding 100 MB are rejected by GitHub; consider using Git LFS or upload the large GIF as a GitHub Release asset.

If you want me to add the large GIF to the repo using Git LFS, compress the animation to a smaller WebM, or include screenshots in this README, tell me which and I'll proceed.

Last updated: 2025-09-28

