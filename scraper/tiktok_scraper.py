import json
import logging
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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
) -> tuple[list[str], str]:
    """
    Navigate to a TikTok slideshow URL and return (image_url_list, error_message).
    error_message is empty string on success.
    """
    logger.info("Navigating to: %s", url)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=page_timeout_ms)
        logger.debug("Page loaded — title: %s", page.title())

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
                    "  if (document.querySelector('#captcha-verify-image, .captcha_verify_container, [id*=\"captcha\"]')) return false;"
                    "  return true;"
                    "}",
                    timeout=captcha_timeout_ms,
                )
                logger.info("CAPTCHA resolved for: %s", url)
            except Exception:
                logger.error("CAPTCHA timed out after %d ms for: %s", captcha_timeout_ms, url)
                return [], "CAPTCHA not solved — timed out"
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
        return [], f"Browser error: {e}"

    soup = BeautifulSoup(content, "html.parser")

    # 1. __NEXT_DATA__ script tag
    next_data_tag = soup.find("script", id="__NEXT_DATA__")
    if next_data_tag and next_data_tag.string:
        try:
            data = json.loads(next_data_tag.string)
            urls = _extract_image_urls_from_json(data)
            if urls:
                logger.info("Found %d images via __NEXT_DATA__ tag", len(urls))
                return urls, ""
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
                    return urls, ""
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
                        return urls, ""
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
            return urls, ""

    logger.warning("No images found for: %s", url)
    return [], "Not a slideshow or content unavailable"
