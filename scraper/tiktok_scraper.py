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
    """Extract the numeric product ID from a resolved TikTok product URL.

    Handles both `www.tiktok.com/view/product/{id}` and
    `shop.tiktok.com/pdp/{id}` (query string after the ID is ignored).
    """
    match = re.search(r"/(?:view/product|pdp)/(\d+)", url)
    return match.group(1) if match else ""


def _extract_product_title(soup: BeautifulSoup) -> str:
    """Extract the product title from the page's og:title meta tag."""
    tag = soup.find("meta", property="og:title")
    if tag and tag.get("content"):
        return tag["content"].strip()
    return ""


def _extract_image_urls_from_json(data: dict) -> list[str]:
    """Walk known JSON paths to find slideshow image URLs."""
    try:
        item = data["props"]["pageProps"]["itemInfo"]["itemStruct"]
        images = item["imagePost"]["images"]
        urls = [img["imageURL"]["urlList"][0] for img in images if img.get("imageURL", {}).get("urlList")]
        if urls:
            logger.debug("Extracted %d image URLs via itemStruct path", len(urls))
            return urls
    except (KeyError, TypeError, IndexError):
        pass

    raw = json.dumps(data)
    match = re.search(r'"imagePost"\s*:\s*(\{.*?"images"\s*:\s*\[.*?\].*?\})', raw, re.DOTALL)
    if match:
        try:
            image_post = json.loads(match.group(1))
            images = image_post.get("images", [])
            urls = [img["imageURL"]["urlList"][0] for img in images if img.get("imageURL", {}).get("urlList")]
            if urls:
                logger.debug("Extracted %d image URLs via regex JSON path", len(urls))
                return urls
        except Exception:
            pass
    return []


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

        # Shared predicate for both the initial detection and the resolution
        # wait below, so a CAPTCHA is only reported when an actual challenge
        # is visible on the page (TikTok ships a hidden captcha-widget
        # container on ordinary pages, which used to trigger false alarms).
        _captcha_visible_js = (
            "() => {"
            "  const t = document.title.toLowerCase();"
            "  const u = location.href.toLowerCase();"
            "  if (t.includes('security check') || t.includes('captcha')) return true;"
            "  if (u.includes('verify.tiktok.com') || u.includes('captcha')) return true;"
            "  const el = document.querySelector('#captcha-verify-image, .captcha_verify_container, [id*=\"captcha\"]');"
            "  if (el) {"
            "    const s = window.getComputedStyle(el);"
            "    return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null;"
            "  }"
            "  return false;"
            "}"
        )

        def _is_captcha_page() -> bool:
            try:
                return bool(page.evaluate(_captcha_visible_js))
            except Exception:
                return False

        if _is_captcha_page():
            logger.warning("CAPTCHA detected on: %s", url)
            if on_captcha:
                on_captcha()
            try:
                page.wait_for_function(
                    f"() => !({_captcha_visible_js})()",
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
