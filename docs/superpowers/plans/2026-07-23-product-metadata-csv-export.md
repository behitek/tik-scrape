# Product Metadata + CSV Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `product_id`/`product_title` from each crawled TikTok product URL, display the title on its row, and write a `products.csv` summary (product_id, title, saved image filenames) into the destination folder on export, with an option to open that folder afterward.

**Architecture:** `scrape_images()` gains a `ScrapeResult` return type carrying the two new fields (extracted from `page.url` and the page's `og:title` meta tag, no extra navigation). `CrawlWorker` emits a new `product_info` signal per URL regardless of success/failure. `UrlRowWidget` swaps its URL-link display text for the title when available. `MainWindow._on_save` gains a new pure `scraper/csv_export.py` module call that writes the CSV alongside the existing image-saving loop, then offers an open-folder button in the completion dialog.

**Tech Stack:** Python 3.10+, PySide6, BeautifulSoup4, Playwright, pytest (new dev dependency for this feature).

## Global Constraints

- CSV must be UTF-8 with BOM (`utf-8-sig`) so Excel renders Vietnamese product titles correctly.
- CSV includes one row per crawled URL, including rows with zero selected images (blank `image_filenames`).
- `image_filenames` cell is a semicolon-and-space-joined list (`"; ".join(...)`) of basenames only, not full paths.
- `products.csv` always overwrites any existing file of that name in the destination folder (no incrementing).
- No changes to the existing image-extraction logic (`__NEXT_DATA__`/regex/DOM fallback chain).
- App is Windows-only; `os.startfile` is an acceptable platform dependency for the open-folder action.

---

### Task 1: `ScrapeResult` dataclass + `_extract_product_id`

**Files:**
- Modify: `scraper/tiktok_scraper.py`
- Test: `tests/test_tiktok_scraper.py` (new)
- Modify: `pyproject.toml` (add pytest dev dependency)

**Interfaces:**
- Produces: `scraper.tiktok_scraper.ScrapeResult` dataclass with fields `images: list[str]`, `error: str`, `product_id: str`, `product_title: str`.
- Produces: `scraper.tiktok_scraper._extract_product_id(url: str) -> str`.

- [ ] **Step 1: Add pytest as a dev dependency**

Run: `uv add --dev pytest`
Expected: `pyproject.toml` gains a `[dependency-groups]` / `dev` entry with `pytest`, and `uv.lock` updates.

- [ ] **Step 2: Create the test file with failing tests**

Create `tests/test_tiktok_scraper.py`:

```python
from scraper.tiktok_scraper import _extract_product_id


def test_extract_product_id_from_product_url():
    url = "https://www.tiktok.com/view/product/1733446332351743967?_svg=1&scene=pdp"
    assert _extract_product_id(url) == "1733446332351743967"


def test_extract_product_id_missing_returns_empty_string():
    url = "https://www.tiktok.com/@someuser/video/7123456789012345678"
    assert _extract_product_id(url) == ""
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: FAIL — `ImportError: cannot import name '_extract_product_id'`

- [ ] **Step 4: Add the dataclass and function to `scraper/tiktok_scraper.py`**

At the top of the file, add the `dataclass` import and insert the new dataclass/function right after the existing imports (before `_extract_image_urls_from_json`):

```python
import json
import logging
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    images: list[str]
    error: str
    product_id: str
    product_title: str


def _extract_product_id(url: str) -> str:
    """Extract the numeric product ID from a resolved TikTok product URL."""
    match = re.search(r"/view/product/(\d+)", url)
    return match.group(1) if match else ""
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock scraper/tiktok_scraper.py tests/test_tiktok_scraper.py
git commit -m "feat: add ScrapeResult dataclass and product_id extraction"
```

---

### Task 2: `_extract_product_title`

**Files:**
- Modify: `scraper/tiktok_scraper.py`
- Modify: `tests/test_tiktok_scraper.py`

**Interfaces:**
- Consumes: `bs4.BeautifulSoup` (already a project dependency, already imported in this file).
- Produces: `scraper.tiktok_scraper._extract_product_title(soup: BeautifulSoup) -> str`.

- [ ] **Step 1: Add failing tests**

Append to `tests/test_tiktok_scraper.py`:

```python
from bs4 import BeautifulSoup

from scraper.tiktok_scraper import _extract_product_title


def test_extract_product_title_from_og_meta():
    html = (
        '<html><head>'
        '<meta property="og:title" content="Áo liền Cardigan dài tay Jiyoo Top AGN017">'
        '</head></html>'
    )
    soup = BeautifulSoup(html, "html.parser")
    assert _extract_product_title(soup) == "Áo liền Cardigan dài tay Jiyoo Top AGN017"


def test_extract_product_title_missing_returns_empty_string():
    soup = BeautifulSoup("<html><head></head></html>", "html.parser")
    assert _extract_product_title(soup) == ""
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: FAIL — `ImportError: cannot import name '_extract_product_title'`

- [ ] **Step 3: Add the function**

In `scraper/tiktok_scraper.py`, add directly after `_extract_product_id`:

```python
def _extract_product_title(soup: BeautifulSoup) -> str:
    """Extract the product title from the page's og:title meta tag."""
    tag = soup.find("meta", property="og:title")
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scraper/tiktok_scraper.py tests/test_tiktok_scraper.py
git commit -m "feat: add product_title extraction from og:title meta tag"
```

---

### Task 3: Wire `scrape_images()` to return `ScrapeResult`

**Files:**
- Modify: `scraper/tiktok_scraper.py`
- Modify: `tests/test_tiktok_scraper.py`

**Interfaces:**
- Consumes: `ScrapeResult`, `_extract_product_id`, `_extract_product_title` (Tasks 1–2).
- Produces: `scrape_images(url, page, on_captcha=None, on_captcha_solved=None, captcha_timeout_ms=180_000, page_timeout_ms=30_000) -> ScrapeResult` (previously returned `tuple[list[str], str]` — this is a breaking signature change consumed in Task 5).

- [ ] **Step 1: Add a failing integration test using a fake Playwright page**

Append to `tests/test_tiktok_scraper.py`:

```python
from scraper.tiktok_scraper import scrape_images, ScrapeResult


class _FakeLocator:
    def count(self):
        return 0


class _FakePage:
    def __init__(self, html: str, url: str):
        self._html = html
        self.url = url

    def goto(self, url, wait_until=None, timeout=None):
        pass

    def title(self):
        return "Product"

    def wait_for_selector(self, selector, timeout=None):
        raise TimeoutError("no slick slider in fake page")

    def content(self):
        return self._html

    def locator(self, selector):
        return _FakeLocator()


def test_scrape_images_returns_scrape_result_with_product_metadata():
    html = (
        '<html><head><meta property="og:title" content="Test Product Title"></head>'
        '<body><script id="__NEXT_DATA__">'
        '{"props": {"pageProps": {"itemInfo": {"itemStruct": {"imagePost": {"images": '
        '[{"imageURL": {"urlList": ["https://example.com/1.jpg"]}}]}}}}}}'
        '</script></body></html>'
    )
    page = _FakePage(html, "https://www.tiktok.com/view/product/1733446332351743967?_svg=1")

    result = scrape_images("https://vt.tiktok.com/shortlink/", page)

    assert result == ScrapeResult(
        images=["https://example.com/1.jpg"],
        error="",
        product_id="1733446332351743967",
        product_title="Test Product Title",
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: FAIL — `scrape_images` still returns a 2-tuple, so the equality assertion against `ScrapeResult` fails.

- [ ] **Step 3: Rewrite `scrape_images()` to build and return `ScrapeResult` at every return point**

Replace the full body of `scrape_images` in `scraper/tiktok_scraper.py` with:

```python
def scrape_images(
    url: str,
    page,
    on_captcha=None,
    on_captcha_solved=None,
    captcha_timeout_ms: int = 180_000,
    page_timeout_ms: int = 30_000,
) -> ScrapeResult:
    """
    Navigate to a TikTok slideshow/product URL and return a ScrapeResult.
    """
    logger.info("Navigating to: %s", url)
    product_id = ""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=page_timeout_ms)
        logger.debug("Page loaded — title: %s", page.title())
        product_id = _extract_product_id(page.url)

        def _is_captcha_page() -> bool:
            title = page.title().lower()
            current_url = page.url.lower()
            if any(x in title for x in ("security check", "captcha", "verify")):
                return True
            if "verify.tiktok.com" in current_url or "captcha" in current_url:
                return True
            try:
                # TikTok slide-puzzle CAPTCHA renders inside a specific container
                if page.locator("#captcha-verify-image, .captcha_verify_container, [id*='captcha']").count() > 0:
                    return True
            except Exception:
                pass
            return False

        if _is_captcha_page():
            logger.warning("CAPTCHA detected on: %s", url)
            if on_captcha:
                on_captcha()
            try:
                page.wait_for_function(
                    "() => {"
                    "  const t = document.title.toLowerCase();"
                    "  const u = location.href.toLowerCase();"
                    "  if (t.includes('security check') || t.includes('captcha') || t.includes('verify')) return false;"
                    "  if (u.includes('verify.tiktok.com') || u.includes('captcha')) return false;"
                    "  const el = document.querySelector('#captcha-verify-image, .captcha_verify_container, [id*=\"captcha\"]');"
                    "  if (el) {"
                    "    const s = window.getComputedStyle(el);"
                    "    const visible = s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null;"
                    "    if (visible) return false;"
                    "  }"
                    "  return true;"
                    "}",
                    timeout=captcha_timeout_ms,
                )
                logger.info("CAPTCHA resolved for: %s", url)
            except Exception:
                try:
                    diag = page.evaluate(
                        "() => {"
                        "  const el = document.querySelector('#captcha-verify-image, .captcha_verify_container, [id*=\"captcha\"]');"
                        "  return {"
                        "    title: document.title,"
                        "    url: location.href,"
                        "    elFound: !!el,"
                        "    elVisible: el ? (window.getComputedStyle(el).display !== 'none'"
                        "      && window.getComputedStyle(el).visibility !== 'hidden'"
                        "      && el.offsetParent !== null) : null,"
                        "  };"
                        "}"
                    )
                    logger.error(
                        "CAPTCHA timed out after %d ms for: %s — page state at timeout: %s",
                        captcha_timeout_ms, url, diag,
                    )
                except Exception as diag_err:
                    logger.error(
                        "CAPTCHA timed out after %d ms for: %s (diagnostic read failed: %s)",
                        captcha_timeout_ms, url, diag_err,
                    )
                return ScrapeResult([], "CAPTCHA not solved — timed out", product_id, "")
            if on_captcha_solved:
                on_captcha_solved()

        try:
            page.wait_for_selector("div.slick-slide", timeout=12000)
            logger.debug("Slick slider found")
        except Exception:
            logger.debug("No slick slider — continuing with content parse")

        content = page.content()
    except Exception as e:
        logger.error("Browser navigation error for %s: %s", url, e, exc_info=True)
        return ScrapeResult([], f"Browser error: {e}", product_id, "")

    soup = BeautifulSoup(content, "html.parser")
    product_title = _extract_product_title(soup)

    # 1. __NEXT_DATA__ script tag
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if next_data_tag and next_data_tag.string:
        try:
            data = json.loads(next_data_tag.string)
            urls = _extract_image_urls_from_json(data)
            if urls:
                logger.info("Found %d images via __NEXT_DATA__ tag", len(urls))
                return ScrapeResult(urls, "", product_id, product_title)
        except json.JSONDecodeError:
            logger.debug("Failed to parse __NEXT_DATA__ tag JSON")

    # 2. JS context evaluation
    for var in ["window.__NEXT_DATA__", "window['SIGI_STATE']", 'window["SIGI_STATE"]']:
        try:
            result = page.evaluate(f"() => JSON.stringify({var})")
            if result:
                data = json.loads(result)
                urls = _extract_image_urls_from_json(data)
                if urls:
                    logger.info("Found %d images via JS eval (%s)", len(urls), var)
                    return ScrapeResult(urls, "", product_id, product_title)
        except Exception as e:
            logger.debug("JS eval failed for %s: %s", var, e)

    # 3. Regex over all script tags
    for script in soup.find_all("script"):
        text = script.string or ""
        for pattern in [
            r'window\["SIGI_STATE"\]\s*=\s*(\{.*\})',
            r'window\.__NEXT_DATA__\s*=\s*(\{.*\})',
        ]:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    urls = _extract_image_urls_from_json(data)
                    if urls:
                        logger.info("Found %d images via script regex fallback", len(urls))
                        return ScrapeResult(urls, "", product_id, product_title)
                except json.JSONDecodeError:
                    pass

    # 4. DOM fallback: Slick slider
    slides = soup.select("div.slick-slide")
    if slides:
        seen: set[str] = set()
        urls = []
        for slide in sorted(slides, key=lambda s: int(s.get("data-index", 0))):
            img = slide.find("img", src=True)
            if img and img["src"] not in seen:
                seen.add(img["src"])
                urls.append(img["src"])
        if urls:
            logger.info("Found %d images via DOM slick-slide fallback", len(urls))
            return ScrapeResult(urls, "", product_id, product_title)

    logger.warning("No images found for: %s", url)
    return ScrapeResult([], "Not a slideshow or content unavailable", product_id, product_title)
```

- [ ] **Step 4: Run all tests in the file to verify they pass**

Run: `uv run pytest tests/test_tiktok_scraper.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add scraper/tiktok_scraper.py tests/test_tiktok_scraper.py
git commit -m "feat: return ScrapeResult with product metadata from scrape_images"
```

---

### Task 4: `scraper/csv_export.py`

**Files:**
- Create: `scraper/csv_export.py`
- Test: `tests/test_csv_export.py` (new)

**Interfaces:**
- Produces: `build_csv_rows(entries: list[tuple[str, str, list[str]]]) -> list[list[str]]` — pure, includes header row.
- Produces: `write_products_csv(dest_dir: str, entries: list[tuple[str, str, list[str]]]) -> str` — writes `products.csv` into `dest_dir`, returns the full path written. `entries` tuples are `(product_id, product_title, filenames)`.
- Consumed by: `ui/main_window.py` in Task 7.

- [ ] **Step 1: Write failing tests**

Create `tests/test_csv_export.py`:

```python
import csv

from scraper.csv_export import build_csv_rows, write_products_csv


def test_build_csv_rows_includes_header_and_semicolon_joined_filenames():
    entries = [
        ("111", "Product One", ["a_001.jpg", "a_002.jpg"]),
        ("222", "Product Two", []),
    ]

    rows = build_csv_rows(entries)

    assert rows == [
        ["product_id", "product_title", "image_filenames"],
        ["111", "Product One", "a_001.jpg; a_002.jpg"],
        ["222", "Product Two", ""],
    ]


def test_write_products_csv_writes_file_readable_back(tmp_path):
    entries = [("111", "Áo Test", ["a_001.jpg"])]

    path = write_products_csv(str(tmp_path), entries)

    assert path == str(tmp_path / "products.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows == [
        ["product_id", "product_title", "image_filenames"],
        ["111", "Áo Test", "a_001.jpg"],
    ]


def test_write_products_csv_overwrites_existing_file(tmp_path):
    write_products_csv(str(tmp_path), [("1", "First", ["x.jpg"])])

    path = write_products_csv(str(tmp_path), [("2", "Second", ["y.jpg"])])

    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    assert rows == [
        ["product_id", "product_title", "image_filenames"],
        ["2", "Second", "y.jpg"],
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_csv_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scraper.csv_export'`

- [ ] **Step 3: Create `scraper/csv_export.py`**

```python
import csv
import os


def build_csv_rows(entries: list[tuple[str, str, list[str]]]) -> list[list[str]]:
    """Build CSV row data (including header) from (product_id, product_title, filenames) entries."""
    rows = [["product_id", "product_title", "image_filenames"]]
    for product_id, product_title, filenames in entries:
        rows.append([product_id, product_title, "; ".join(filenames)])
    return rows


def write_products_csv(dest_dir: str, entries: list[tuple[str, str, list[str]]]) -> str:
    """Write products.csv into dest_dir, overwriting any existing file. Returns the path written."""
    path = os.path.join(dest_dir, "products.csv")
    rows = build_csv_rows(entries)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_csv_export.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scraper/csv_export.py tests/test_csv_export.py
git commit -m "feat: add products.csv writer module"
```

---

### Task 5: Wire `CrawlWorker` to `ScrapeResult` and emit `product_info`

**Files:**
- Modify: `scraper/worker.py:14` (import), `scraper/worker.py:85-89` (signals), `scraper/worker.py:144-165` (scrape call site)

**Interfaces:**
- Consumes: `ScrapeResult` (Task 3).
- Produces: `CrawlWorker.product_info` — `Signal(str, str, str)` emitting `(url, product_id, product_title)`, emitted once per URL right after `scrape_images()` returns (or after the except-fallback), regardless of success/error. Consumed by `ui/main_window.py` in Task 7.

No automated test for this task: it's Qt signal wiring around already-tested logic (`ScrapeResult`, `scrape_images`), and this codebase has no Qt test harness (`pytest-qt` is not a dependency and none of the UI/worker code has existing tests — introducing one is out of scope for this feature). Verified via an import/syntax check here and end-to-end manual verification in Task 7.

- [ ] **Step 1: Update the import**

In `scraper/worker.py`, change line 14:

```python
from scraper.tiktok_scraper import scrape_images
```

to:

```python
from scraper.tiktok_scraper import scrape_images, ScrapeResult
```

- [ ] **Step 2: Add the new signal**

In `scraper/worker.py`, change the signal block (lines 85-89):

```python
class CrawlWorker(QThread):
    images_ready     = Signal(str, list)
    status_update    = Signal(str, str)
    progress         = Signal(int, int)
    captcha_detected = Signal(str)   # url — triggers sound/tray in main thread
```

to:

```python
class CrawlWorker(QThread):
    images_ready     = Signal(str, list)
    status_update    = Signal(str, str)
    progress         = Signal(int, int)
    captcha_detected = Signal(str)   # url — triggers sound/tray in main thread
    product_info     = Signal(str, str, str)  # url, product_id, product_title
```

- [ ] **Step 3: Update the scrape call site to use `ScrapeResult` and emit `product_info`**

In `scraper/worker.py`, replace (lines 144-165):

```python
                try:
                    image_urls, error = scrape_images(
                        url, page,
                        on_captcha=_on_captcha,
                        on_captcha_solved=_on_captcha_solved,
                        captcha_timeout_ms=cfg["captcha_timeout_ms"],
                        page_timeout_ms=cfg["page_timeout"] * 1000,
                    )
                except Exception as e:
                    logger.error("Scrape error for %s: %s", url, e, exc_info=True)
                    error = f"Unexpected error: {e}"
                    image_urls = []

                if error or not image_urls:
```

with:

```python
                try:
                    result = scrape_images(
                        url, page,
                        on_captcha=_on_captcha,
                        on_captcha_solved=_on_captcha_solved,
                        captcha_timeout_ms=cfg["captcha_timeout_ms"],
                        page_timeout_ms=cfg["page_timeout"] * 1000,
                    )
                except Exception as e:
                    logger.error("Scrape error for %s: %s", url, e, exc_info=True)
                    result = ScrapeResult([], f"Unexpected error: {e}", "", "")

                self.product_info.emit(url, result.product_id, result.product_title)
                image_urls, error = result.images, result.error

                if error or not image_urls:
```

- [ ] **Step 4: Sanity-check the module imports and compiles**

Run: `uv run python -c "import scraper.worker"`
Expected: no output, exit code 0

- [ ] **Step 5: Commit**

```bash
git add scraper/worker.py
git commit -m "feat: emit product_info signal from CrawlWorker"
```

---

### Task 6: `UrlRowWidget` product title display

**Files:**
- Modify: `ui/url_row_widget.py:14-18` (`__init__`), `ui/url_row_widget.py:40-82` (`_build_top_bar`), add new methods after `set_status`

**Interfaces:**
- Produces: `UrlRowWidget.product_id: str` (default `""`), `UrlRowWidget.product_title: str` (default `""`), `UrlRowWidget.set_product_info(product_id: str, title: str) -> None`. Consumed by `ui/main_window.py` in Task 7 (for the signal slot) and by the CSV-export entry building (`row.product_id`, `row.product_title`).

No automated test for this task (Qt widget rendering; no `pytest-qt` in this project). Verified manually in Task 7's end-to-end check.

- [ ] **Step 1: Add the new attributes to `__init__`**

In `ui/url_row_widget.py`, change (lines 14-18):

```python
    def __init__(self, url: str, index: int, parent=None):
        super().__init__(parent)
        self.url = url
        self.thumbs: list[ImageThumb] = []
```

to:

```python
    def __init__(self, url: str, index: int, parent=None):
        super().__init__(parent)
        self.url = url
        self.thumbs: list[ImageThumb] = []
        self.product_id = ""
        self.product_title = ""
```

- [ ] **Step 2: Store the URL label as an attribute and extract its text-building into a helper**

In `ui/url_row_widget.py`, replace the URL label construction block inside `_build_top_bar` (lines 50-65):

```python
        # Clickable URL label
        display = escape(self.url[:65] + ("…" if len(self.url) > 65 else ""))
        url_label = QLabel(
            f'<a href="{escape(self.url)}" '
            f'style="color:{PALETTE["text_dim"]}; text-decoration:none;">'
            f'{display}</a>'
        )
        url_label.setOpenExternalLinks(True)
        url_label.setToolTip(self.url)
        url_label.setCursor(Qt.CursorShape.PointingHandCursor)
        url_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; }} "
            f"QLabel:hover {{ color: {PALETTE['teal']}; }}"
        )
        url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(url_label)
```

with:

```python
        # Clickable URL/title label — text refreshed by _refresh_url_label()
        self._url_label = QLabel()
        self._url_label.setOpenExternalLinks(True)
        self._url_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; }} "
            f"QLabel:hover {{ color: {PALETTE['teal']}; }}"
        )
        self._url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._refresh_url_label()
        top.addWidget(self._url_label)
```

- [ ] **Step 3: Add `set_product_info` and `_refresh_url_label` methods**

In `ui/url_row_widget.py`, add these methods right after `set_status` (after line 117, before `add_images`):

```python
    def set_product_info(self, product_id: str, title: str):
        self.product_id = product_id
        self.product_title = title
        self._refresh_url_label()

    def _refresh_url_label(self):
        text_source = self.product_title or self.url
        display = escape(text_source[:65] + ("…" if len(text_source) > 65 else ""))
        self._url_label.setText(
            f'<a href="{escape(self.url)}" '
            f'style="color:{PALETTE["text_dim"]}; text-decoration:none;">'
            f'{display}</a>'
        )
        tooltip_lines = []
        if self.product_title:
            tooltip_lines.append(self.product_title)
        if self.product_id:
            tooltip_lines.append(f"Product ID: {self.product_id}")
        tooltip_lines.append(self.url)
        self._url_label.setToolTip("\n".join(tooltip_lines))
```

- [ ] **Step 4: Sanity-check the module imports and compiles**

Run: `uv run python -c "import ui.url_row_widget"`
Expected: no output, exit code 0

- [ ] **Step 5: Commit**

```bash
git add ui/url_row_widget.py
git commit -m "feat: display product title on scraper rows"
```

---

### Task 7: `MainWindow` — wire signal, CSV export, open-folder dialog

**Files:**
- Modify: `ui/main_window.py:18` (import), `ui/main_window.py:274-281` (`_on_crawl` signal connections), add `_on_product_info` slot after `_on_status_update`, modify `_on_save` (lines 365-394)

**Interfaces:**
- Consumes: `CrawlWorker.product_info` (Task 5), `UrlRowWidget.set_product_info` / `.product_id` / `.product_title` (Task 6), `write_products_csv` (Task 4).

- [ ] **Step 1: Import `write_products_csv`**

In `ui/main_window.py`, change line 18:

```python
from scraper.worker import CrawlWorker
```

to:

```python
from scraper.worker import CrawlWorker
from scraper.csv_export import write_products_csv
```

- [ ] **Step 2: Connect the new signal in `_on_crawl`**

In `ui/main_window.py`, change (lines 274-281):

```python
        urls = [row.url for row in self._rows]
        self._worker = CrawlWorker(urls, config=config)
        self._worker.images_ready.connect(self._on_images_ready)
        self._worker.status_update.connect(self._on_status_update)
        self._worker.progress.connect(self._on_progress)
        self._worker.captcha_detected.connect(self._on_captcha_detected)
        self._worker.finished.connect(self._on_crawl_finished)
        self._worker.start()
```

to:

```python
        urls = [row.url for row in self._rows]
        self._worker = CrawlWorker(urls, config=config)
        self._worker.images_ready.connect(self._on_images_ready)
        self._worker.status_update.connect(self._on_status_update)
        self._worker.progress.connect(self._on_progress)
        self._worker.captcha_detected.connect(self._on_captcha_detected)
        self._worker.product_info.connect(self._on_product_info)
        self._worker.finished.connect(self._on_crawl_finished)
        self._worker.start()
```

- [ ] **Step 3: Add the `_on_product_info` slot**

In `ui/main_window.py`, add this method directly after `_on_status_update` (after line 299):

```python
    def _on_product_info(self, url: str, product_id: str, product_title: str):
        for row in self._rows:
            if row.url == url:
                row.set_product_info(product_id, product_title)
                break
```

- [ ] **Step 4: Rewrite `_on_save` to build CSV entries and add the open-folder dialog**

In `ui/main_window.py`, replace the full `_on_save` method (lines 365-394):

```python
    def _on_save(self):
        dest = self._dest_edit.text().strip() or self._dest_folder
        os.makedirs(dest, exist_ok=True)

        saved = 0
        errors = 0
        for row in self._rows:
            selected = [t for t in row.thumbs if t.selected]
            if not selected:
                continue
            prefix = row.prefix_edit.text().strip() or "image"
            for i, thumb in enumerate(selected, 1):
                filename = f"{prefix}_{i:03d}.jpg"
                filepath = os.path.join(dest, filename)
                stem, ext = os.path.splitext(filepath)
                counter = 1
                while os.path.exists(filepath):
                    filepath = f"{stem}_{counter}{ext}"
                    counter += 1
                ok = thumb.full_pixmap.save(filepath, "JPEG", 92)
                if ok:
                    saved += 1
                else:
                    errors += 1

        logger.info("Đã lưu %d ảnh vào %s (%d lỗi)", saved, dest, errors)
        msg = f"Đã lưu {saved} ảnh vào:\n{dest}"
        if errors:
            msg += f"\n\n⚠ {errors} ảnh không thể lưu."
        QMessageBox.information(self, "Lưu xong", msg)
```

with:

```python
    def _on_save(self):
        dest = self._dest_edit.text().strip() or self._dest_folder
        os.makedirs(dest, exist_ok=True)

        saved = 0
        errors = 0
        csv_entries = []
        for row in self._rows:
            selected = [t for t in row.thumbs if t.selected]
            saved_filenames = []
            prefix = row.prefix_edit.text().strip() or "image"
            for i, thumb in enumerate(selected, 1):
                filename = f"{prefix}_{i:03d}.jpg"
                filepath = os.path.join(dest, filename)
                stem, ext = os.path.splitext(filepath)
                counter = 1
                while os.path.exists(filepath):
                    filepath = f"{stem}_{counter}{ext}"
                    counter += 1
                ok = thumb.full_pixmap.save(filepath, "JPEG", 92)
                if ok:
                    saved += 1
                    saved_filenames.append(os.path.basename(filepath))
                else:
                    errors += 1
            csv_entries.append((row.product_id, row.product_title, saved_filenames))

        logger.info("Đã lưu %d ảnh vào %s (%d lỗi)", saved, dest, errors)

        csv_error = ""
        try:
            write_products_csv(dest, csv_entries)
        except OSError as e:
            csv_error = str(e)
            logger.error("Không thể ghi products.csv: %s", e)

        msg = f"Đã lưu {saved} ảnh vào:\n{dest}"
        if errors:
            msg += f"\n\n⚠ {errors} ảnh không thể lưu."
        if csv_error:
            msg += f"\n\n⚠ Không thể ghi products.csv: {csv_error}"

        box = QMessageBox(self)
        box.setWindowTitle("Lưu xong")
        box.setText(msg)
        box.setIcon(QMessageBox.Icon.Information)
        open_btn = box.addButton("Mở thư mục", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() == open_btn:
            os.startfile(dest)
```

- [ ] **Step 5: Sanity-check the module imports and compiles**

Run: `uv run python -c "import ui.main_window"`
Expected: no output, exit code 0

- [ ] **Step 6: Run the full test suite**

Run: `uv run pytest -v`
Expected: PASS (all tests from Tasks 1–4, no regressions)

- [ ] **Step 7: Manual end-to-end verification**

Run: `uv run python main.py`

1. Paste 2-3 URLs from `urls.txt` into the input box and click "Bắt đầu".
2. If a CAPTCHA appears in the browser window, solve it manually (existing app behavior, unchanged by this feature).
3. Confirm each row's link text switches from the raw URL to the product title once the title is extracted, and that hovering shows a tooltip with the full title, `Product ID: ...`, and the URL.
4. Select a few images across at least two rows (leave at least one row with zero selections), choose a destination folder, click "Lưu đã chọn".
5. Confirm the completion dialog shows both "Mở thư mục" and "OK" buttons.
6. Click "Mở thư mục" and confirm Windows Explorer opens the destination folder.
7. Open `products.csv` in that folder (Excel or a text editor) and confirm: one row per crawled URL (including the zero-selection row with a blank `image_filenames` cell), correct `product_id`/`product_title` values, semicolon-joined filenames matching the actual saved `.jpg` files, and Vietnamese characters rendering correctly (not mojibake).

- [ ] **Step 8: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: export products.csv and add open-folder option on save"
```

---

## Self-Review Notes

- **Spec coverage:** product_id extraction (Task 1), product_title extraction (Task 2), integrated into `scrape_images` (Task 3), CSV writer module (Task 4), worker signal (Task 5), UI title display (Task 6), MainWindow wiring + CSV export + open-folder button (Task 7) — all spec sections have a corresponding task.
- **Placeholder scan:** no TBD/TODO markers; every step has complete, runnable code.
- **Type consistency:** `ScrapeResult` fields (`images`, `error`, `product_id`, `product_title`) are used identically across Tasks 1, 3, 5. `write_products_csv(dest_dir, entries)` / `build_csv_rows(entries)` signatures match between Task 4's definition and Task 7's call site (`entries` as `list[tuple[str, str, list[str]]]`, matching `csv_entries` built in `_on_save`). `UrlRowWidget.set_product_info(product_id, title)` matches the call in Task 7's `_on_product_info`.
