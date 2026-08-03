# TikTok Product Images Downloader

A Windows desktop app for bulk-downloading images from TikTok slideshow (photo) posts. Load a list of TikTok URLs, crawl them all, pick the images you want from a thumbnail grid, and save them to a local folder.

## Features

- Bulk-load TikTok URLs from a `.txt` file or `.xlsx` spreadsheet
- Crawls posts in a persistent browser session and extracts slideshow images
- Per-URL thumbnail grid with click-to-select and hover preview
- Optional filename prefix per URL/row
- Pauses and prompts for manual action if TikTok shows a CAPTCHA
- Exports a `products.csv` alongside the downloaded images

## Requirements

- Windows
- [uv](https://docs.astral.sh/uv/) for dependency management
- Python (managed automatically by `uv`, see `pyproject.toml` for the supported range)

## Getting started

```bash
# Install dependencies
uv sync

# Install the Playwright browser (first run only)
uv run playwright install chromium

# Run the app
uv run python main.py
```

## Usage

1. Launch the app and load a `.txt` file (one URL per line) or an `.xlsx` file with a `url` column (and optional `prefix` column). Use **Download Template** to generate a sample spreadsheet.
2. Click **Crawl All** to fetch images for every loaded URL.
3. Click thumbnails to select the images you want to keep for each row.
4. Click **Save Selected** and choose a destination folder — selected images are saved as JPEGs, prefixed by each row's prefix, along with a `products.csv` summary.

## Architecture

```
main.py                   # Entry point: QApplication setup + first-run Chromium install
scraper/
  tiktok_scraper.py       # Core extraction: Playwright + JSON/__NEXT_DATA__ parsing
  worker.py               # QThread worker: runs scraping, downloads images, emits Qt signals
  csv_export.py           # Writes products.csv for saved images
ui/
  main_window.py          # Main window: file loading, toolbar, row list, save flow
  url_row_widget.py        # One row per URL: prefix field, status label, thumbnail strip
  image_thumb.py          # Clickable thumbnail: selection state, hover popup preview
```

See `CLAUDE.md` for a more detailed breakdown of the threading model and scraping strategy.

## Building a distributable

See [DEPLOY.md](DEPLOY.md) for instructions on building a standalone `.exe`, portable ZIP, and Windows installer with PyInstaller and NSIS.

## Testing

```bash
uv run pytest
```

## License

Proprietary.
