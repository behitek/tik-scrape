import base64
import json
import logging
import random
import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from scraper.captcha_solver import (
    SUBTYPE_3D, SUBTYPE_TWO_OBJECTS, CaptchaSolver, CaptchaSolverError,
)

logger = logging.getLogger(__name__)

_IMAGE_FETCH_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Shared predicate for both the initial detection and the resolution wait, so
# a CAPTCHA is only reported when an actual challenge is visible on the page
# (TikTok ships a hidden captcha-widget container on ordinary pages, which
# used to trigger false alarms).
_CAPTCHA_VISIBLE_JS = (
    "() => {"
    "  const t = document.title.toLowerCase();"
    "  const u = location.href.toLowerCase();"
    "  if (t.includes('security check') || t.includes('captcha')) return true;"
    "  if (u.includes('verify.tiktok.com') || u.includes('captcha')) return true;"
    "  const sels = ['#captcha-verify-image', '.captcha_verify_container'];"
    "  for (const sel of sels) {"
    "    for (const el of document.querySelectorAll(sel)) {"
    "      const s = window.getComputedStyle(el);"
    "      if (s.display === 'none' || s.visibility === 'hidden') continue;"
    "      const r = el.getBoundingClientRect();"
    "      if (r.width > 0 && r.height > 0) return true;"
    "    }"
    "  }"
    "  return false;"
    "}"
)

# Reads everything needed to hand a challenge to the solver and to apply the
# answer afterwards: subtype, image sources, and on-screen geometry.
_CAPTCHA_STATE_JS = """() => {
  const isVisible = (el) => {
    if (!el) return false;
    const s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return {x: r.x, y: r.y, w: r.width, h: r.height};
  };
  const container = document.querySelector('.captcha_verify_container');
  if (!isVisible(container)) return null;

  const text = (container.innerText || '').toLowerCase();
  const pieceEl = container.querySelector('.captcha_verify_img_slide, [class*="img_slide"]');
  let subtype = null;
  if (isVisible(pieceEl)) subtype = 'puzzle';
  else if (text.includes('puzzle') || text.includes('piece') || text.includes('mảnh ghép')) subtype = 'puzzle';
  else if (text.includes('rotate') || text.includes('xoay')) subtype = 'rotate';
  else if (text.includes('3d')) subtype = '3d';
  else if (text.includes('two') || text.includes('objects') || text.includes('vật thể')) subtype = 'two_objects';

  let imageEl = container.querySelector('#captcha-verify-image')
    || container.querySelector('.captcha_verify_img--wrapper img, .captcha_verify_img--wrapper canvas, canvas, img');
  let imageSrc = null;
  if (imageEl) {
    if (imageEl.tagName === 'CANVAS') imageSrc = imageEl.toDataURL('image/png');
    else imageSrc = imageEl.currentSrc || imageEl.src || null;
  }
  if (!imageSrc) {
    const bgHolder = container.querySelector('[style*="background-image"], [class*="captcha_verify_img"]');
    if (bgHolder) {
      const m = (window.getComputedStyle(bgHolder).backgroundImage || '').match(/url\\(["']?(.*?)["']?\\)/);
      if (m) imageSrc = m[1];
    }
  }
  const pieceSrc = pieceEl ? (pieceEl.currentSrc || pieceEl.src || null) : null;

  const thumbEl = container.querySelector('.secsdk-captcha-drag-icon, [class*="drag-icon"]')
    || container.querySelector('.captcha_verify_slide--button')
    || container.querySelector('.captcha_verify_slide--slidebar');
  const sliderEl = container.querySelector('.captcha_verify_slide--slidebar')
    || container.querySelector('.captcha_verify_slide--button');

  return {
    subtype: subtype,
    text: (container.innerText || '').slice(0, 160),
    imageSrc: imageSrc,
    pieceSrc: pieceSrc,
    imageRect: imageEl ? rect(imageEl) : null,
    pieceRect: pieceEl ? rect(pieceEl) : null,
    natural: imageEl ? {w: imageEl.naturalWidth || 0, h: imageEl.naturalHeight || 0} : null,
    thumbRect: thumbEl ? rect(thumbEl) : null,
    sliderRect: sliderEl ? rect(sliderEl) : null,
  };
}"""


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


class WafRedirectError(Exception):
    """TikTok's WAF kept redirecting the navigation to its login page."""


_WAF_MAX_ATTEMPTS = 3
_WAF_BACKOFF_MS = (3000, 6000)  # random range, multiplied by the attempt number


def _goto_with_retry(page, url: str, timeout_ms: int, max_attempts: int = _WAF_MAX_ATTEMPTS) -> None:
    """page.goto that retries when TikTok's WAF bounces us to /login.

    The redirect is intermittent and per-request (the same URL works on the
    next try), so waiting a few seconds and navigating again is enough.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if "/login" not in str(page.url):
                return
            reason = "redirected to login page"
        except Exception as e:
            if "interrupted by another navigation" not in str(e):
                raise
            reason = "navigation interrupted by login redirect"

        if attempt == max_attempts:
            raise WafRedirectError(reason)
        delay = random.randint(*_WAF_BACKOFF_MS) * attempt
        logger.warning(
            "WAF %s for %s — retry %d/%d in %.1fs",
            reason, url, attempt, max_attempts - 1, delay / 1000,
        )
        page.wait_for_timeout(delay)


def _short_error(e: Exception, limit: int = 140) -> str:
    first_line = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
    return first_line if len(first_line) <= limit else first_line[: limit - 1] + "…"


# ── Automatic CAPTCHA solving ───────────────────────────────────────────────


def _read_captcha_state(page) -> dict | None:
    """Return the visible challenge's DOM/geometry, or None if not shown."""
    try:
        return page.evaluate(_CAPTCHA_STATE_JS)
    except Exception as e:
        logger.debug("Could not read CAPTCHA state: %s", e)
        return None


def _wait_for_captcha_state(page, timeout_ms: int = 5_000) -> dict | None:
    """Wait briefly for the widget DOM to appear after a challenge signalled."""
    state = _read_captcha_state(page)
    waited = 0
    while state is None and waited < timeout_ms:
        try:
            if not page.evaluate(_CAPTCHA_VISIBLE_JS):
                return None
        except Exception:
            return None
        page.wait_for_timeout(300)
        waited += 300
        state = _read_captcha_state(page)
    return state


def _wait_for_captcha_assets(page, state: dict | None, timeout_ms: int = 8_000) -> dict | None:
    """Wait until the challenge image (and puzzle piece) have a src.

    The widget container can become visible a moment before its images load;
    submitting an empty base64 image would waste an API call and fall back to
    manual for no reason.
    """
    def ready(s: dict | None) -> bool:
        if not s or not s.get("imageSrc"):
            return False
        if s.get("subtype") == "puzzle" and not s.get("pieceSrc"):
            return False
        return True

    waited = 0
    while state is not None and not ready(state) and waited < timeout_ms:
        page.wait_for_timeout(250)
        waited += 250
        state = _read_captcha_state(page)
    return state


def _fetch_image_b64(page, src: str | None) -> str:
    """Fetch a challenge image and return it as base64 (or data URI)."""
    if not src:
        return ""
    if src.startswith("data:"):
        return src
    if src.startswith("blob:"):
        try:
            return page.evaluate(
                "async (u) => {"
                "  const blob = await (await fetch(u)).blob();"
                "  return await new Promise((resolve, reject) => {"
                "    const reader = new FileReader();"
                "    reader.onload = () => resolve(reader.result);"
                "    reader.onerror = () => reject(reader.error);"
                "    reader.readAsDataURL(blob);"
                "  });"
                "}",
                src,
            )
        except Exception as e:
            logger.warning("Could not read blob CAPTCHA image: %s", e)
            return ""
    try:
        resp = requests.get(
            src,
            timeout=20,
            headers={"User-Agent": _IMAGE_FETCH_UA, "Referer": "https://www.tiktok.com/"},
        )
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode("ascii")
    except Exception as e:
        logger.warning("Could not download CAPTCHA image %s: %s", src[:100], e)
        return ""


def _drag_distance(state: dict, solution) -> float | None:
    """Convert a solver solution into a horizontal slider drag in CSS pixels."""
    slider = state.get("sliderRect") or {}

    # Rotate challenges: the returned angle is mapped onto the full slider
    # travel (TikTok's rotate slider sweeps 360° end to end).
    if solution.angle is not None and solution.x is None:
        thumb = state.get("thumbRect") or {}
        slider_w = float(slider.get("w") or 0)
        thumb_w = float(thumb.get("w") or 0)
        if slider_w and abs(thumb_w - slider_w) < 2:
            # fallback element is the whole bar; knob size ≈ bar height
            thumb_w = float(thumb.get("h") or slider.get("h") or 44)
        track = max(1.0, slider_w - thumb_w)
        return track * (solution.angle % 360.0) / 360.0

    image_rect = state.get("imageRect") or {}
    display_w = float(image_rect.get("w") or 0)

    # The returned position is an absolute x within the image, but the piece
    # may not start at the image's left edge. Only the difference has to be
    # covered by the slider drag.
    piece_offset = 0.0
    piece_rect = state.get("pieceRect") or {}
    if display_w and piece_rect.get("w"):
        piece_offset = float(piece_rect.get("x", 0)) - float(image_rect.get("x", 0))

    # `proportion` is the target position relative to the image width and is
    # already independent of the image's natural resolution.
    if solution.proportion is not None and display_w:
        return solution.proportion * display_w - piece_offset

    if solution.x is not None:
        natural_w = float((state.get("natural") or {}).get("w") or 0)
        if display_w and natural_w:
            return solution.x * display_w / natural_w - piece_offset
        return solution.x

    return None


def _human_drag(page, start_x: float, start_y: float, dx: float, dy: float = 0.0):
    """Drag with a slight ease-out curve and jitter instead of a teleport."""
    page.mouse.move(start_x, start_y)
    page.wait_for_timeout(random.randint(80, 180))
    page.mouse.down()
    page.wait_for_timeout(random.randint(60, 140))

    steps = random.randint(18, 30)
    for i in range(1, steps + 1):
        t = i / steps
        eased = 1 - (1 - t) ** 3
        x = start_x + dx * eased + random.uniform(-0.6, 0.6)
        y = start_y + dy * eased + random.uniform(-0.5, 0.5)
        page.mouse.move(x, y)
        page.wait_for_timeout(random.randint(8, 22))

    page.wait_for_timeout(random.randint(80, 180))
    page.mouse.up()


def _apply_captcha_solution(page, state: dict, solution) -> bool:
    """Perform the mouse gesture that answers the challenge."""
    distance = _drag_distance(state, solution)
    if distance is None or distance <= 1:
        logger.warning(
            "CAPTCHA solution has no usable position: %s (state subtype=%s)",
            solution.raw, state.get("subtype"),
        )
        return False

    slider = state.get("sliderRect") or {}
    thumb = state.get("thumbRect") or slider
    if not thumb:
        logger.warning("CAPTCHA slider not found — cannot apply solution")
        return False

    # If only the whole slider bar was found, the knob can only be at its
    # left end (where it starts); dragging from the bar's centre would grab
    # nothing and the challenge would never move.
    fallback_knob = bool(slider) and abs(
        float(thumb.get("w") or 0) - float(slider.get("w") or 0)
    ) < 2
    if fallback_knob:
        knob_w = min(float(slider.get("h") or 44), float(thumb.get("w") or 44))
        start_x = float(slider["x"]) + knob_w / 2
        start_y = float(slider["y"]) + float(slider.get("h") or 44) / 2
        logger.info("CAPTCHA knob element not found — dragging from the bar's left end")
    else:
        knob_w = float(thumb.get("w") or 0)
        start_x = thumb["x"] + thumb["w"] / 2
        start_y = thumb["y"] + thumb["h"] / 2

    max_travel = float(slider.get("w") or 0) - knob_w
    if max_travel > 0:
        if distance > max_travel + 2:
            logger.warning(
                "Required drag %.1f px exceeds slider travel %.1f px — cannot apply",
                distance, max_travel,
            )
            return False
        distance = min(distance, max_travel)

    logger.info(
        "Applying CAPTCHA solution %s — dragging %.1f px from (%.1f, %.1f)",
        solution.raw, distance, start_x, start_y,
    )
    _human_drag(page, start_x, start_y, distance)
    return True


def _wait_captcha_gone(page, timeout_ms: int) -> bool:
    try:
        page.wait_for_function(
            f"() => !({_CAPTCHA_VISIBLE_JS})()",
            timeout=timeout_ms,
        )
        return True
    except Exception:
        # Navigation can destroy the execution context; re-read the state.
        try:
            return not page.evaluate(_CAPTCHA_VISIBLE_JS)
        except Exception:
            return _read_captcha_state(page) is None


def _auto_solve_captcha(
    page,
    solver: CaptchaSolver,
    on_solving=None,
    max_attempts: int = 2,
    solve_timeout_ms: int = 12_000,
) -> bool:
    """Try to solve the visible CAPTCHA automatically.

    Each attempt reads a fresh challenge from the page, asks the resolver for
    an answer, and performs the drag. Returns True only when the challenge
    actually disappears.
    """
    for attempt in range(1, max_attempts + 1):
        state = _read_captcha_state(page)
        if state is None:
            # The challenge may have just been signalled while its widget is
            # still rendering; give it a moment before deciding.
            state = _wait_for_captcha_state(page)
        if state is None:
            try:
                visible = bool(page.evaluate(_CAPTCHA_VISIBLE_JS))
            except Exception:
                return True
            if visible:
                logger.warning(
                    "CAPTCHA is visible but no usable challenge widget was found "
                    "— falling back to manual"
                )
                return False
            return True

        # These need object selection/clicks that this client cannot drive
        # yet — don't spend solver credits on them.
        if state.get("subtype") in (SUBTYPE_3D, SUBTYPE_TWO_OBJECTS):
            logger.warning(
                "CAPTCHA subtype %r needs manual interaction — falling back",
                state.get("subtype"),
            )
            return False

        state = _wait_for_captcha_assets(page, state)
        if state is None:
            try:
                return not bool(page.evaluate(_CAPTCHA_VISIBLE_JS))
            except Exception:
                return True

        if attempt == 1 and on_solving:
            on_solving()

        logger.info(
            "Auto-solving CAPTCHA (attempt %d/%d, subtype=%s)",
            attempt, max_attempts, state.get("subtype") or "auto",
        )
        image_b64 = _fetch_image_b64(page, state.get("imageSrc"))
        if not image_b64:
            logger.warning("No CAPTCHA image could be captured — falling back to manual")
            return False
        piece_b64 = _fetch_image_b64(page, state.get("pieceSrc")) or None

        try:
            solution = solver.solve_tiktok(
                image_b64,
                piece_b64=piece_b64,
                subtype=state.get("subtype"),
            )
        except CaptchaSolverError as e:
            logger.error("CAPTCHA resolver failed: %s", e)
            return False
        except Exception:
            logger.exception("Unexpected CAPTCHA resolver error")
            return False

        if not _apply_captcha_solution(page, state, solution):
            return False

        if _wait_captcha_gone(page, solve_timeout_ms):
            logger.info("CAPTCHA solved automatically on attempt %d", attempt)
            return True

        logger.warning("CAPTCHA still visible after attempt %d — retrying", attempt)
        page.wait_for_timeout(1200)

    try:
        return not bool(page.evaluate(_CAPTCHA_VISIBLE_JS))
    except Exception:
        return True


def scrape_images(
    url: str,
    page,
    on_captcha=None,
    on_captcha_solved=None,
    captcha_timeout_ms: int = 180_000,
    page_timeout_ms: int = 30_000,
    captcha_solver: CaptchaSolver | None = None,
    on_captcha_auto=None,
) -> ScrapeResult:
    """
    Navigate to a TikTok slideshow/product URL and return a ScrapeResult.

    When ``captcha_solver`` is supplied, a detected challenge is answered
    automatically; if that fails, behaviour falls back to the manual wait.
    """
    logger.info("Navigating to: %s", url)
    product_id = ""
    try:
        _goto_with_retry(page, url, page_timeout_ms)
        logger.debug("Page loaded — title: %s", page.title())
        product_id = _extract_product_id(page.url)

        def _is_captcha_page() -> bool:
            try:
                return bool(page.evaluate(_CAPTCHA_VISIBLE_JS))
            except Exception:
                return False

        def _handle_captcha() -> ScrapeResult | None:
            """Auto-solve or wait for a challenge; error result on timeout."""
            if not _is_captcha_page():
                return None

            logger.warning("CAPTCHA detected on: %s", url)
            if _read_captcha_state(page) is None:
                logger.warning(
                    "CAPTCHA is visible but its widget is not ready/recognized yet "
                    "(title=%r, url=%r)",
                    page.title(), page.url,
                )

            auto_solved = False
            if captcha_solver is not None and captcha_solver.configured:
                try:
                    auto_solved = _auto_solve_captcha(
                        page, captcha_solver, on_solving=on_captcha_auto
                    )
                except Exception:
                    logger.exception("Auto CAPTCHA solving failed — falling back to manual")

            if not auto_solved:
                if on_captcha:
                    on_captcha()
                try:
                    page.wait_for_function(
                        f"() => !({_CAPTCHA_VISIBLE_JS})()",
                        timeout=captcha_timeout_ms,
                    )
                    logger.info("CAPTCHA resolved for: %s", url)
                except Exception:
                    try:
                        diag = page.evaluate(
                            "() => {"
                            "  const out = [];"
                            "  for (const sel of ['#captcha-verify-image', '.captcha_verify_container', '[id*=\"captcha\"]']) {"
                            "    for (const el of document.querySelectorAll(sel)) {"
                            "      const s = window.getComputedStyle(el), r = el.getBoundingClientRect();"
                            "      out.push({id: el.id, cls: (el.className || '').toString().slice(0, 60),"
                            "        display: s.display, visibility: s.visibility,"
                            "        w: Math.round(r.width), h: Math.round(r.height)});"
                            "    }"
                            "  }"
                            "  return {title: document.title, url: location.href, elements: out.slice(0, 10)};"
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
            return None

        # TikTok usually injects the challenge several seconds after
        # domcontentloaded, so keep watching for it while waiting for content.
        content_deadline = time.monotonic() + min(page_timeout_ms / 1000, 15.0)
        while True:
            captcha_error = _handle_captcha()
            if captcha_error is not None:
                return captcha_error

            try:
                has_content = bool(page.evaluate(
                    "() => {"
                    "  const d = document.querySelector('#__NEXT_DATA__');"
                    "  if (d && d.textContent && d.textContent.includes('imagePost')) return true;"
                    "  return !!document.querySelector('div.slick-slide');"
                    "}"
                ))
            except Exception:
                has_content = False

            if has_content:
                logger.debug("Page content ready")
                break
            if time.monotonic() >= content_deadline:
                logger.debug("Content wait timed out — continuing with content parse")
                break
            page.wait_for_timeout(350)

        # A challenge can also arrive just after the content renders.
        captcha_error = _handle_captcha()
        if captcha_error is not None:
            return captcha_error

        content = page.content()
    except WafRedirectError as e:
        logger.error("TikTok WAF login redirect persisted for %s (%s)", url, e)
        return ScrapeResult(
            [], "TikTok chuyển hướng sang trang đăng nhập (WAF) — hãy chạy lại", product_id, ""
        )
    except Exception as e:
        logger.error("Browser navigation error for %s: %s", url, e, exc_info=True)
        return ScrapeResult([], f"Browser error: {_short_error(e)}", product_id, "")

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
