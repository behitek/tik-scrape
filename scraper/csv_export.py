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
