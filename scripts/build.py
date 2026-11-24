"""Build the public static catalog using Python's standard library."""
from hashlib import sha256
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


def validate_event_prices(prices, path):
    if not isinstance(prices, dict) or not prices or prices.keys() - {"standard", "techbookfest"}:
        raise ValueError(f"Invalid eventPrices profile: {path}")
    for profile, amounts in prices.items():
        if not isinstance(amounts, dict) or not amounts or amounts.keys() - {"紙＋電子", "電子"}:
            raise ValueError(f"Invalid eventPrices formats for {profile}: {path}")
        if any(type(amount) is not int or amount < 0 for amount in amounts.values()):
            raise ValueError(f"Expected a nonnegative yen amount for {profile}: {path}")


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


def blog_header(books):
    settings = read_json(ROOT / "data/blog-header.json")
    book = next((b for b in books if b["id"] == settings["bookId"]), None)
    if book is None:
        raise ValueError(f"Unknown blog header book: {settings['bookId']}")
    shop = next((s for s in book["shops"] if s["shop"] == settings["shop"] and not s.get("sold")), None)
    if shop is None:
        raise ValueError(f"Missing available blog header shop for {book['id']}: {settings['shop']}")
    filename = settings["image"]
    if not re.fullmatch(re.escape(book["id"]) + r"(?:-[a-z0-9_-]+)?\.png", filename):
        raise ValueError(f"Invalid blog header image for {book['id']}: {filename}")
    image = "blog-banners/" + filename
    version = sha256((ROOT / "web" / image).read_bytes()).hexdigest()[:16]
    return {"title": book["title"], "url": shop["url"], "image": f"{image}?v={version}"}


def build():
    books = []
    for path in sorted((ROOT / "data/books").glob("*.json")):
        book = read_json(path)
        if "eventPrices" in book:
            validate_event_prices(book.pop("eventPrices"), path)
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
        if book["genre"] == "tech":
            topics = book.get("topics")
            if not isinstance(topics, list) or not topics or any(t not in ("infra", "ai") for t in topics):
                raise ValueError(f"Expected tech topics (infra or ai): {path}")
        for shop in book["shops"]:
            if urlsplit(shop["url"]).scheme not in {"https", "http"}:
                raise ValueError(f"Invalid purchase URL: {path}")
            prices = shop.get("prices", {})
            sold_formats = shop.get("soldOutFormats", [])
            if not isinstance(sold_formats, list) or any(
                not isinstance(form, str) or form not in prices for form in sold_formats
            ):
                raise ValueError(f"soldOutFormats must list keys from prices: {path}, {shop['url']}")
            if prices and all(form in sold_formats for form in prices):
                shop["sold"] = True
            available = {form: price for form, price in prices.items() if form not in sold_formats}
            if shop["shop"] == "booth" and not shop.get("sold"):
                shop["receipts"] = {form: booth_receipt(price, form)
                                    for form, price in available.items()}
            if shop["shop"] == "amazon" and "kdp" in shop and not shop.get("sold"):
                shop["receipts"] = {form: kdp_receipt(price, form, shop["kdp"])
                                    for form, price in available.items()
                                    if not (form == "紙" and shop.get("paperPublisher") == "NextPublishing")}
        books.append(book)
    book_ids = {book["id"] for book in books}
    for path in sorted((ROOT / "data/bundles").glob("*.json")):
        bundle = read_json(path)
        if bundle.get("id") != path.stem or path.stem in book_ids:
            raise ValueError(f"Invalid bundle ID: {path}")
        members = bundle.get("bookIds")
        if (not isinstance(members, list) or len(members) < 2
                or any(not isinstance(key, str) or key not in book_ids for key in members)
                or len(set(members)) != len(members)):
            raise ValueError(f"Expected distinct catalog book IDs in bookIds: {path}")
        validate_event_prices(bundle.get("eventPrices"), path)
    books.sort(key=lambda book: book["order"])
    examples = read_json(ROOT / "data/receipt-examples.json")
    for group in examples["groups"]:
        if group["id"] not in {book["id"] for book in books}:
            raise ValueError(f"Unknown receipt example: {group['id']}")
        for offer in group["offers"]:
            offer["amount"] = receipt(offer)
    banner = blog_header(books)
    DIST.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "web", DIST, dirs_exist_ok=True)
    (DIST / "blog-header.json").write_text(json.dumps(banner, ensure_ascii=False), encoding="utf-8")
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
