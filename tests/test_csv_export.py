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
