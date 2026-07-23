from scraper.tiktok_scraper import _extract_product_id


def test_extract_product_id_from_product_url():
    url = "https://www.tiktok.com/view/product/1733446332351743967?_svg=1&scene=pdp"
    assert _extract_product_id(url) == "1733446332351743967"


def test_extract_product_id_missing_returns_empty_string():
    url = "https://www.tiktok.com/@someuser/video/7123456789012345678"
    assert _extract_product_id(url) == ""
