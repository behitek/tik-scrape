# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

TikTok product image scraper — a Windows desktop app that bulk-downloads images from TikTok slideshow posts. Users load a `.txt` or `.xlsx` file of URLs, crawl them all, pick images from the thumbnail grid, and save selected images to a local folder.

## Commands

```bash
# Install dependencies
uv sync

# Run the app
uv run python main.py

# Install Playwright browsers (required on first run)
uv run playwright install chromium
```

## Architecture

```
main.py                   # Entry: QApplication setup + launches MainWindow
scraper/
  tiktok_scraper.py       # Core extraction: Playwright + JSON/__NEXT_DATA__ parsing + CAPTCHA auto-solve
  captcha_solver.py       # CaptchaSolve API client (createTask/getTaskResult)
  worker.py               # QThread worker: runs scraping, downloads images, emits Qt signals
ui/
  main_window.py          # Main window: file loading, toolbar, row list, save flow
  url_row_widget.py       # One row per URL: prefix field, status label, thumbnail strip
  image_thumb.py          # Clickable thumbnail: selection state, hover popup preview
```

**Threading model:** Qt main thread owns the UI. `CrawlWorker(QThread)` runs the scraping loop in a background thread and communicates back via Qt signals (`images_ready`, `status_update`, `progress`). Images are downloaded and converted to `QPixmap` inside the worker before being emitted.

**Scraping strategy (tiktok_scraper.py):** Playwright navigates to each URL in a persistent Chrome profile (`~/.tik-scrape-profile`). Images are extracted in priority order:
1. `__NEXT_DATA__` script tag → JSON walk via `itemStruct.imagePost.images`
2. `window.__NEXT_DATA__` via JS evaluation
3. Regex extraction from all script tags
4. DOM fallback: Slick slider `<div>` elements

**CAPTCHA handling:** detection checks the page title/URL and whether a captcha container is actually visible. If an API key is configured, `scraper/tiktok_scraper.py::_auto_solve_captcha` captures the challenge image (and puzzle piece), sends it to the CaptchaSolve API, then performs a human-like slider drag using the returned position. If solving fails or no key is set, the worker signals the UI and waits up to 3 minutes for manual resolution.

**CaptchaSolve API** (`scraper/captcha_solver.py`, base `https://api.kimidev.net`):
- `POST /api/solve/createTask` with `{"clientKey", "task": {"type": "TikTokCaptchaTask", "image": <base64>, "piece": <base64, puzzle only>, "subtype": "puzzle"|"rotate"|"3d"|"two_objects"}}`
- `POST /api/solve/getTaskResult` with `{"clientKey", "taskId"}` — poll until `status` is `1`/`"ready"` and `solution` is present
- `POST /api/solve/getBalance` with `{"clientKey"}` — used by the Settings tab's **Kiểm tra** button
- Puzzle solutions return `{"x", "target_x", "distance", "proportion"}` where `proportion = x / natural_image_width`; drag the slider by `proportion * displayed_image_width`. Rotate returns `{"angle": degrees}`.
- The API key is user-entered and stored in `QSettings` (`captcha/api_key`, `captcha/auto_solve`) from the **Cài đặt → Xử lý CAPTCHA** tab. Never hardcode or commit keys.

## Key data flow

1. `MainWindow._on_load_file()` parses `.txt`/`.xlsx` → creates one `UrlRowWidget` per URL
2. "Crawl All" instantiates `CrawlWorker(urls)` and calls `.start()`
3. Worker emits `images_ready(url, pixmap_pairs)` → `UrlRowWidget.add_images()` populates thumbnails
4. "Save Selected" collects checked `ImageThumb` widgets, writes full-size pixmaps as JPEG to the chosen folder, prefixed by the row's prefix input

## Excel template format

Column `url` (required) + column `prefix` (optional). `MainWindow._on_download_template()` generates a sample file. The parser auto-detects headers case-insensitively.
