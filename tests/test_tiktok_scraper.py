from bs4 import BeautifulSoup

from scraper.tiktok_scraper import (
    _extract_product_id, _extract_product_title, _goto_with_retry, _short_error,
    scrape_images, ScrapeResult,
)


def test_extract_product_id_from_product_url():
    url = "https://www.tiktok.com/view/product/1733446332351743967?_svg=1&scene=pdp"
    assert _extract_product_id(url) == "1733446332351743967"


def test_extract_product_id_from_shop_pdp_url():
    url = "https://shop.tiktok.com/pdp/1733446332351743967?_d=1&other=params"
    assert _extract_product_id(url) == "1733446332351743967"


def test_extract_product_id_missing_returns_empty_string():
    url = "https://www.tiktok.com/@someuser/video/7123456789012345678"
    assert _extract_product_id(url) == ""


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


class _WafPage(_FakePage):
    """Fails `fail_times` navigations with the WAF interruption, then succeeds."""

    def __init__(self, fail_times: int, mode: str = "raise"):
        super().__init__("<html></html>", "https://www.tiktok.com/view/product/1")
        self.fail_times = fail_times
        self.mode = mode
        self.goto_calls = 0
        self.waits = []

    def goto(self, url, wait_until=None, timeout=None):
        self.goto_calls += 1
        if self.goto_calls <= self.fail_times:
            if self.mode == "raise":
                raise RuntimeError(
                    'Page.goto: Navigation to "x" is interrupted by another navigation to "https://www.tiktok.com/login/?a=b"'
                )
            self.url = "https://www.tiktok.com/login/?enter_method=waf_force_login"
        else:
            self.url = "https://www.tiktok.com/view/product/1"

    def wait_for_timeout(self, ms):
        self.waits.append(ms)


def test_goto_retries_after_waf_interruption():
    page = _WafPage(fail_times=2)
    _goto_with_retry(page, "https://vt.tiktok.com/x", 30000)
    assert page.goto_calls == 3
    assert len(page.waits) == 2


def test_goto_retries_when_landing_on_login_page():
    page = _WafPage(fail_times=1, mode="redirect")
    _goto_with_retry(page, "https://vt.tiktok.com/x", 30000)
    assert page.goto_calls == 2


def test_scrape_images_reports_waf_error_after_retries_exhausted():
    page = _WafPage(fail_times=99)
    result = scrape_images("https://vt.tiktok.com/x", page)
    assert page.goto_calls == 3
    assert result.images == []
    assert "WAF" in result.error


def test_short_error_keeps_first_line_and_truncates():
    assert _short_error(RuntimeError("a" * 500 + "\nsecond")) .endswith("…")
    assert len(_short_error(RuntimeError("a" * 500))) == 140
    assert _short_error(RuntimeError("one\ntwo")) == "one"
