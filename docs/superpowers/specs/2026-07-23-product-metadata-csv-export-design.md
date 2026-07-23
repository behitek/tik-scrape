# Product metadata + CSV export — design

## Problem

The scraper currently extracts only slideshow images per URL. TikTok Shop product URLs (`vt.tiktok.com/...` short links that redirect to `https://www.tiktok.com/view/product/{product_id}`) also carry a product title and numeric product ID that the user wants captured, shown in the UI, and recorded alongside the exported images.

## Goals

- Extract `product_id` and `product_title` for every crawled URL, using the same page load already performed for image scraping (no extra navigation).
- Display product title (not just the raw URL) on each row in the UI.
- On "Save Selected", in addition to copying selected images, write a `products.csv` into the destination folder with one row per crawled URL: `product_id`, `product_title`, and the semicolon-joined list of saved image filenames (basenames only) for that product — including rows where zero images were selected.
- After a successful save, offer a button to open the destination folder.

## Non-goals

- No change to image extraction logic (`__NEXT_DATA__` / regex / DOM fallback chain) — it already works for these URLs.
- No retry/backfill mechanism for rows scraped before this change.
- No historical/append CSV — each save overwrites `products.csv` with the current full state.

## Extraction design

### `product_id`

Parsed via regex `r"/view/product/(\d+)"` against `page.url` **after** navigation completes (TikTok resolves the `vt.tiktok.com` short link to the `/view/product/{id}` URL by the time `domcontentloaded` fires). Empty string if the pattern isn't found (e.g. CAPTCHA never resolved, or a non-product URL).

### `product_title`

Parsed from `<meta property="og:title" content="...">` in the already-parsed `soup` object (the same BeautifulSoup instance built for image extraction). Confirmed present on TikTok product-page redirects via the `og_info` share parameter. Chosen over a JSON-tree search because the exact `__NEXT_DATA__`/`SIGI_STATE` schema for product pages was not verified live (CAPTCHA blocked inspection) — a meta tag is a stabler, simpler dependency than an unconfirmed JSON path. Empty string if the tag is missing.

### Return shape

`scrape_images()` currently returns `tuple[list[str], str]` (images, error). This grows to a small dataclass:

```python
@dataclass
class ScrapeResult:
    images: list[str]
    error: str
    product_id: str
    product_title: str
```

All existing call sites (`worker.py`) update to unpack the dataclass instead of a 2-tuple.

## Threading / signals

`CrawlWorker` gains a new signal:

```python
product_info = Signal(str, str, str)  # url, product_id, product_title
```

Emitted immediately after `scrape_images()` returns, **before** the existing error/image-download branching — so every URL gets a `product_info` emission regardless of whether images were found, error occurred, or CAPTCHA timed out. This guarantees every row has whatever metadata was extractable, independent of image success, which the CSV export depends on (it must cover every crawled product).

## UI changes

### `UrlRowWidget`

- New attributes: `self.product_id = ""`, `self.product_title = ""`.
- New method `set_product_info(product_id: str, title: str)`:
  - Stores the values.
  - If `title` is non-empty, replaces the row's URL-link display text with the title (truncated to the same ~65 char limit as the URL currently uses), keeping the `<a href="...">` pointing at the original URL so it's still clickable.
  - If `title` is empty, leaves the URL displayed (current behavior, unchanged).
  - Tooltip on the label is updated to show: full title (if any) + `Product ID: {id}` (if any) + full URL.

### `MainWindow`

- New slot `_on_product_info(url, product_id, product_title)`: finds the matching row by `row.url == url` (same pattern as `_on_images_ready` / `_on_status_update`) and calls `row.set_product_info(...)`.
- Connected in `_on_crawl()` alongside the other worker signal connections.

## Export changes (`_on_save`)

Current behavior saves each row's selected images as `{prefix}_{i:03d}.jpg`, auto-incrementing on filename collision. This is unchanged. Added on top:

1. While saving, track the actual saved basename(s) per row (post-collision-resolution) in a `dict[UrlRowWidget, list[str]]` (or a parallel list built during the existing save loop).
2. After the image-save loop completes, write `products.csv` into `dest`:
   - Columns: `product_id`, `product_title`, `image_filenames`.
   - One row per entry in `self._rows`, in existing row order — including rows with an empty filename list.
   - `image_filenames` cell = `"; ".join(filenames)` (empty string if none saved/selected).
   - File encoded `utf-8-sig` (BOM) so Excel renders Vietnamese titles correctly, using Python's `csv` module (handles quoting for any stray `;`/`,`/newline in titles automatically).
   - Always overwrites any existing `products.csv` in `dest` (no incrementing filename — unlike images, this file represents current full state, not a discrete new artifact).
3. CSV write is wrapped in a try/except; failure is reported in the same summary dialog as image-save errors, without blocking the rest of the export.

### Post-save dialog

Replace the current `QMessageBox.information(...)` with a `QMessageBox` configured with two buttons: **OK** and **Mở thư mục** (Open folder). Clicking "Mở thư mục" calls `os.startfile(dest)` (Windows-only app, consistent with existing platform assumptions).

## Error handling summary

- Missing `product_id`/`product_title` never blocks scraping, image download, or save — cells are just blank in the UI/CSV.
- CSV write failure doesn't block image saving (image loop runs first) and is surfaced as an additional line in the completion message, same pattern as existing `errors` count for failed image writes.

## Testing

- Manual verification against the existing `urls.txt` sample list: confirm title displays per row, `products.csv` is created with correct columns/encoding (Vietnamese text readable in Excel), row count matches crawled URL count, filenames match what's actually on disk, and "Mở thư mục" opens the right folder.
- No existing automated test suite in this repo to extend (none found under the project).
