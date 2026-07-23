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
  tiktok_scraper.py       # Core extraction: Playwright + JSON/__NEXT_DATA__ parsing
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

CAPTCHA detection is handled by checking page text; the worker pauses and signals the UI while waiting up to 3 minutes for manual resolution.

## Key data flow

1. `MainWindow._on_load_file()` parses `.txt`/`.xlsx` → creates one `UrlRowWidget` per URL
2. "Crawl All" instantiates `CrawlWorker(urls)` and calls `.start()`
3. Worker emits `images_ready(url, pixmap_pairs)` → `UrlRowWidget.add_images()` populates thumbnails
4. "Save Selected" collects checked `ImageThumb` widgets, writes full-size pixmaps as JPEG to the chosen folder, prefixed by the row's prefix input

## Excel template format

Column `url` (required) + column `prefix` (optional). `MainWindow._on_download_template()` generates a sample file. The parser auto-detects headers case-insensitively.
