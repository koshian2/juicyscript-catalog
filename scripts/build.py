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


def booth_receipt(price, form):
    """One item, no BOOST. Round each fee up independently to whole yen."""
    if type(price) is not int or price < 0:
        raise ValueError(f"Invalid BOOTH price: {price}")
    if form not in {"紙", "紙＋電子", "電子"} or (price == 0 and form != "電子"):
        return None
    if price == 0:
        return 0
    service = (price * 56 + 999) // 1000 + 45
    warehouse = 0 if form == "電子" else (price * 25 + 999) // 1000 + 25
    return price - service - warehouse


def kdp_receipt(price, form, terms):
    """Estimate one retail sale on Amazon.co.jp from a tax-inclusive list price."""
    if type(price) is not int or price < 0:
        raise ValueError(f"Invalid KDP price: {price}")
    net = Decimal(price) / Decimal("1.10")
    if form in {"紙", "紙＋電子"}:
        cost = terms.get("printing")
        if cost is None:
            return None
        if type(cost) is not int or cost < 0:
            raise ValueError(f"Invalid KDP printing cost: {cost}")
        rate = Decimal("0.60") if net >= 1000 else Decimal("0.50")
        return int((net * rate - cost).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if form != "電子" and not form.startswith("電子（"):
        return None
    rate = terms.get("ebookRate")
    if price == 0:
        return 0
    if not 250 <= price <= 1650:
        rate = 35
    if rate is None:
        return None
    if rate not in (35, 70):
        raise ValueError(f"Invalid KDP ebook rate: {rate}")
    delivery = terms.get("delivery") if rate == 70 else 0
    if delivery is None:
        return None
    if type(delivery) is not int or delivery < 0:
        raise ValueError(f"Invalid KDP delivery cost: {delivery}")
    royalty = (net - delivery) * rate / 100
    # KDP rounds yen royalties up from a fractional part of 0.46.
    return int(royalty + Decimal("0.54"))


def receipt(offer):
    """Reproduce the historical public sheet, including its original BOOTH fees."""
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
    elif shop == "Amazon" and offer.get("publisher") == "KDP":
        return kdp_receipt(offer["price"], "紙", offer)
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
            if shop["shop"] == "booth" and not shop.get("sold"):
                shop["receipts"] = {form: booth_receipt(price, form)
                                    for form, price in shop.get("prices", {}).items()}
            if shop["shop"] == "amazon" and "kdp" in shop and not shop.get("sold"):
                shop["receipts"] = {form: kdp_receipt(price, form, shop["kdp"])
                                    for form, price in shop.get("prices", {}).items()
                                    if not (form == "紙" and shop.get("paperPublisher") == "NextPublishing")}
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
