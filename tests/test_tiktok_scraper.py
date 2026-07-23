from bs4 import BeautifulSoup

from scraper.tiktok_scraper import _extract_product_id, _extract_product_title, scrape_images, ScrapeResult


def test_extract_product_id_from_product_url():
    url = "https://www.tiktok.com/view/product/1733446332351743967?_svg=1&scene=pdp"
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
