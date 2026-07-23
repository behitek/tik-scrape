from bs4 import BeautifulSoup

from scraper.tiktok_scraper import _extract_product_id, _extract_product_title


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
