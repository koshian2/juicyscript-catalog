"""Build the public static catalog using Python's standard library."""
from html import escape
import json
import re
import shutil
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def receipt(offer):
    if "publishedAmount" in offer:
        return offer["publishedAmount"]
    price = Decimal(offer["price"])
    paper = offer["format"] == "紙"
    shop = offer["shop"]
    if shop == "Booth":
        amount = price * Decimal("0.944") - 22 - (26 if paper else 0)
    elif shop in ("とら", "メロン"):
        amount = price * Decimal("0.7")
    elif shop == "技術書典OM":
        amount = (price - (100 if paper else 0)) * Decimal("0.8")
    elif shop == "おもバザハンズ":
        amount = price * Decimal("0.65")
    elif shop == "Amazon" and not paper:
        amount = price / Decimal("1.1") * Decimal("0.35")
    else:
        raise ValueError(f"Unknown receipt rule: {offer}")
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def build():
    books = []
    for path in sorted((ROOT / "data/books").glob("*.json")):
        book = read_json(path)
        # Keep the published catalog format compatible with existing widgets.
        blog = book["blog"]
        if isinstance(blog, dict):
            book["blog"] = blog.get("enabled")
            book["order"] = blog.get("order", 0)
        if type(book["blog"]) is not bool or type(book.get("order")) is not int:
            raise ValueError(f"Invalid blog settings (expected boolean enabled and integer order): {path}")
        if not re.fullmatch(r"[a-z0-9_-]+", path.stem) or book["id"] != path.stem:
            raise ValueError(f"Invalid book ID: {path}")
        if book["cover"] != f"covers/{path.stem}.jpg" or not (ROOT / book["cover"]).is_file():
            raise ValueError(f"Missing cover: {path}")
        if book["genre"] not in {"tech", "eki", "goods"}:
            raise ValueError(f"Unknown genre: {path}")
        for shop in book["shops"]:
            if urlsplit(shop["url"]).scheme not in {"https", "http"}:
                raise ValueError(f"Invalid purchase URL: {path}")
        books.append(book)
    books.sort(key=lambda book: book["order"])
    examples = read_json(ROOT / "data/receipt-examples.json")
    for group in examples["groups"]:
        if group["id"] not in {book["id"] for book in books}:
            raise ValueError(f"Unknown receipt example: {group['id']}")
        for offer in group["offers"]:
            offer["amount"] = receipt(offer)
    DIST.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "web", DIST, dirs_exist_ok=True)
    (DIST / "covers").mkdir(exist_ok=True)
    descriptions = DIST / "descriptions"
    descriptions.mkdir(exist_ok=True)
    for book in books:
        source = ROOT / "data/books" / (book["id"] + ".html")
        if source.exists():
            body = source.read_text(encoding="utf-8")
        else:
            body = "".join(f"<p>{escape(line)}</p>" for line in book["description"].splitlines())
        paragraphs = list(re.finditer(r"</p>", body, re.IGNORECASE))
        split = paragraphs[2].end() if len(paragraphs) > 3 else len(body)
        book["introHtml"] = body[:split]
        book["moreHtml"] = body[split:].strip()
        book["descriptionUrl"] = "descriptions/" + book["id"] + ".html"
        document = ('<!doctype html><html lang="ja"><meta charset="utf-8">'
                    '<base target="_blank"><link rel="stylesheet" href="../portal/honoka.css">'
                    f'<title>{escape(book["title"])}</title><body>{body}</body></html>')
        (DIST / book["descriptionUrl"]).write_text(document, encoding="utf-8")
        shutil.copyfile(ROOT / book["cover"], DIST / book["cover"])
    catalog = {"books": books, "receipts": examples}
    (DIST / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    print(f"Built {len(books)} catalog entries in {DIST}")


if __name__ == "__main__":
    build()
