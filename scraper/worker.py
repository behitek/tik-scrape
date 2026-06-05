import logging
import random
import time
import traceback
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap, QImage

from scraper.tiktok_scraper import scrape_images

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PROFILE_DIR = Path.home() / ".tik-scrape-profile"
_PROFILE_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"})

_DEFAULT_CONFIG = {
    "human_sim": False,
    "min_delay": 0.5,
    "max_delay": 2.0,
    "page_timeout": 30,
    "captcha_timeout_ms": 180_000,
}


def _url_to_pixmaps(image_url: str) -> tuple[QPixmap, QPixmap] | None:
    try:
        resp = SESSION.get(image_url, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        logger.warning("Failed to download image %s: %s", image_url, e)
        return None

    full = img.copy()
    max_dim = 1200
    if max(full.width, full.height) > max_dim:
        full.thumbnail((max_dim, max_dim), Image.LANCZOS)
    full_px = _pil_to_pixmap(full)

    thumb = img.copy()
    thumb.thumbnail((120, 120), Image.LANCZOS)
    thumb_px = _pil_to_pixmap(thumb)

    return thumb_px, full_px


def _pil_to_pixmap(img: Image.Image) -> QPixmap:
    data = img.tobytes("raw", "RGB")
    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


def _human_simulate(page, config: dict):
    """Perform random mouse movements and a scroll to mimic human behaviour."""
    if not config.get("human_sim"):
        return
    try:
        for _ in range(random.randint(2, 4)):
            x = random.randint(150, 1100)
            y = random.randint(100, 650)
            page.mouse.move(x, y)
            page.wait_for_timeout(random.randint(120, 450))
        scroll_px = random.randint(80, 350)
        page.evaluate(f"window.scrollBy(0, {scroll_px})")
        page.wait_for_timeout(random.randint(200, 600))
        logger.debug("Human simulation: moved mouse and scrolled %dpx", scroll_px)
    except Exception as e:
        logger.debug("Human simulation step skipped: %s", e)


class CrawlWorker(QThread):
    images_ready     = Signal(str, list)
    status_update    = Signal(str, str)
    progress         = Signal(int, int)
    captcha_detected = Signal(str)   # url — triggers sound/tray in main thread

    def __init__(self, url_list: list[str], config: dict | None = None, parent=None):
        super().__init__(parent)
        self._urls = url_list
        self._config = {**_DEFAULT_CONFIG, **(config or {})}
        self._stop = False

    def stop(self):
        self._stop = True
        logger.info("Stop requested by user")

    def run(self):
        total = len(self._urls)
        logger.info("Crawl started — %d URL(s)", total)

        try:
            self._run_inner(total)
        except Exception:
            logger.critical("Unexpected worker crash:\n%s", traceback.format_exc())

        logger.info("Crawl finished")

    def _run_inner(self, total: int):
        cfg = self._config
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(_PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                user_agent=_UA,
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
            )
            page = ctx.new_page()

            for i, url in enumerate(self._urls, 1):
                if self._stop:
                    logger.info("Crawl stopped at URL %d/%d", i, total)
                    break

                self.status_update.emit(url, "Fetching…")
                logger.info("[%d/%d] Processing: %s", i, total, url)

                def _on_captcha():
                    self.status_update.emit(url, "⚠ CAPTCHA — solve in browser window to continue")
                    self.captcha_detected.emit(url)

                def _on_captcha_solved():
                    self.status_update.emit(url, "CAPTCHA solved, extracting…")

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
                    self.status_update.emit(url, f"⚠ {error or 'No images found'}")
                    self.progress.emit(i, total)
                    _human_simulate(page, cfg)
                    delay = random.uniform(cfg["min_delay"], cfg["max_delay"])
                    logger.debug("Waiting %.1fs before next URL", delay)
                    time.sleep(max(delay, 0.3))
                    continue

                self.status_update.emit(url, f"Downloading {len(image_urls)} image(s)…")
                logger.debug("Downloading %d images", len(image_urls))

                pairs = []
                for img_url in image_urls:
                    result = _url_to_pixmaps(img_url)
                    if result:
                        pairs.append(result)

                if pairs:
                    self.images_ready.emit(url, pairs)
                    self.status_update.emit(url, f"✓ {len(pairs)} image(s)")
                    logger.info("Done: %d images downloaded for %s", len(pairs), url)
                else:
                    self.status_update.emit(url, "⚠ Images could not be downloaded")
                    logger.warning("All image downloads failed for: %s", url)

                self.progress.emit(i, total)

                _human_simulate(page, cfg)
                delay = random.uniform(cfg["min_delay"], cfg["max_delay"])
                logger.debug("Waiting %.1fs before next URL", delay)
                time.sleep(max(delay, 0.1))

            ctx.close()
