const catalogUrl = new URL("./catalog.json", import.meta.url);
const shopNames = {booth:"BOOTH", amazon:"Amazon", tbf:"技術書典", melon:"メロンブックス", dlsite:"DLsite", note:"note"};

function node(tag, className, text) {
  const item = document.createElement(tag);
  if (className) item.className = className;
  if (text) item.textContent = text;
  return item;
}

function linkTo(url, newTab) {
  const link = node("a");
  link.href = url;
  if (newTab) {
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  }
  return link;
}

function banner(offer) {
  const figure = node("figure", "promo-shop");
  const name = shopNames[offer.shop] || offer.shop;
  const prices = Object.entries(offer.prices ?? {}).map(([kind, amount]) =>
    kind + (offer.soldOutFormats?.includes(kind) ? "完売" : amount + "円")).join("、");
  const caption = offer.caption && !offer.soldOutFormats?.length ? offer.caption :
    [offer.variant, prices, offer.caption].filter(Boolean).join(" ");
  const link = offer.sold ? node("span") : linkTo(offer.url, false);
  const image = node("img", "promo-shop");
  image.alt = name + (offer.sold ? "（販売終了）" : "");
  const soldImage = offer.sold && ["booth", "melon"].includes(offer.shop);
  image.src = new URL("portal/banner/" + offer.shop + (soldImage ? "_sold" : "") + ".png", catalogUrl);
  if (offer.sold && !soldImage) image.style.filter = "grayscale(1)";
  const label = offer.sold && !soldImage ? "販売終了・" + caption : caption;
  link.append(image, node("figcaption", "promo-shop-hover-mask", label));
  figure.append(link);
  return figure;
}

function bookTitle(book) {
  const title = node("h2", "book-title");
  const [main, divider, sub] = book.title.split(/([：:]|――)(.*)/s);
  const line = node("span", "main-title");
  const series = main.match(/^(.*?)(AWS)(（[０-９]+）)$/);
  if (series) {
    const volume = node("span", "series-volume", series[2]);
    volume.append(node("span", "volume", series[3]));
    line.append(series[1], volume);
  } else line.textContent = main;
  title.append(line);
  if (sub) {
    const subtitle = node("span", "subtitle");
    subtitle.append(node("span", "title-separator", divider));
    const phrase = book.subtitleBreakAfter;
    if (phrase && sub.startsWith(phrase)) {
      subtitle.append(node("span", "subtitle-phrase", phrase), node("wbr"),
        node("span", "subtitle-phrase", sub.slice(phrase.length)));
    } else subtitle.append(sub);
    title.append(subtitle);
  }
  return title;
}

function priceTable(book) {
  const formats = [...new Set(book.shops.flatMap(offer => Object.keys(offer.prices || {})))];
  const order = ["紙＋電子", "紙", "電子"];
  formats.sort((a,b) => (order.includes(a) ? order.indexOf(a) : 3) - (order.includes(b) ? order.indexOf(b) : 3));
  const table = node("table", "price-matrix");
  table.setAttribute("aria-label", book.title + "の購入先と価格");
  const header = table.createTHead().insertRow();
  for (const label of ["ストア", ...(formats.length ? formats : ["価格・形態"])]) {
    const th = node("th", "", label);
    th.scope = "col";
    header.append(th);
  }
  const body = table.createTBody();
  for (const offer of book.shops) {
    const row = body.insertRow();
    const store = node("th");
    store.scope = "row";
    const logo = node("img");
    logo.alt = shopNames[offer.shop] || offer.shop;
    const sold = offer.sold && ["booth","melon"].includes(offer.shop);
    logo.src = new URL("portal/banner/" + offer.shop + (sold ? "_sold" : "") + ".png", catalogUrl);
    if (offer.sold) store.append(logo, node("small", "", "販売終了"));
    else {
      const link = linkTo(offer.url, true);
      link.className = "store-link";
      link.append(logo);
      store.append(link);
    }
    if (offer.variant) store.append(node("small", "", offer.variant));
    row.append(store);
    if (offer.caption && !offer.soldOutFormats?.length) {
      const cell = row.insertCell();
      cell.colSpan = Math.max(1, formats.length);
      cell.className = "terms";
      cell.textContent = offer.caption;
    } else for (const format of formats) {
      const cell = row.insertCell();
      const price = offer.prices[format];
      if (price === undefined) {
        cell.className = "empty";
        cell.textContent = "—";
      } else if (offer.soldOutFormats?.includes(format)) {
        cell.textContent = "完売";
      } else cell.append(price.toLocaleString("ja-JP"), node("small", "", "円"));
    }
    if (offer.caption && offer.soldOutFormats?.length) store.append(node("small", "", offer.caption));
  }
  return table;
}

function portalBooks(books, genre) {
  const english = genre === "tech-en";
  const content = document.createDocumentFragment();
  const today = new Date();
  let lastHeading;
  for (const book of books) {
    const [year, month] = book.published.split("/").map(Number);
    const age = (today.getFullYear() - year) * 12 + today.getMonth() + 1 - month;
    const recent = age >= 0 && age <= 12;
    const heading = english ? (recent ? "New releases" : "Backlist") :
      genre === "goods" ? (recent ? "新作" : "グッズ") : (recent ? "新刊" : "既刊");
    const article = node("article", "book");
    const cover = node("div", "cover-well");
    const availableShop = book.shops.find(offer => !offer.sold);
    const coverLink = availableShop ? linkTo(availableShop.url, true) : node("span");
    const image = node("img", "cover-image");
    image.src = new URL(book.cover, catalogUrl);
    image.alt = english ? "Cover of " + book.title : book.title + "の表紙";
    coverLink.append(image);
    cover.append(coverLink);
    const copy = node("div", "copy");
    if (heading !== lastHeading) copy.append(node("h1", recent ? "shelf release" : "shelf", heading));
    lastHeading = heading;
    const synopsis = node("div", "synopsis");
    // These fragments are built from the repository's public description files.
    synopsis.innerHTML = book.introHtml;
    if (book.moreHtml) {
      const details = node("details");
      details.innerHTML = book.moreHtml;
      details.prepend(node("summary", "", english ? "Read more" : "目次・紹介の続きを読む"));
      synopsis.append(details);
    }
    const purchase = node("div", "purchase");
    purchase.append(node("h3", "", english ? "Where to buy" : "購入先・価格"));
    if (english) {
      const links = node("div", "edition-links");
      for (const offer of book.shops) {
        const link = linkTo(offer.url, true);
        link.textContent = offer.variant + " · " + new URL(offer.url).hostname.replace(/^www\./, "");
        links.append(link);
      }
      purchase.append(links);
    } else purchase.append(priceTable(book));
    const issued = english ? new Date(year, month - 1).toLocaleDateString("en-US", {month:"long", year:"numeric"}) : year + "年" + month + "月発行";
    copy.append(node("p", "issued", issued), bookTitle(book), synopsis, purchase);
    article.append(cover, copy);
    content.append(article);
  }
  return content;
}
function techBooks(books) {
  const controls = node("div", "tech-filters");
  controls.setAttribute("role", "group");
  controls.setAttribute("aria-label", "技術書の分野");
  const list = node("div");
  list.append(portalBooks(books, "tech"));
  for (const [topic, label] of [["all", "すべて"], ["infra", "インフラ"], ["ai", "AI・機械学習"]]) {
    const button = node("button", "", label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(topic === "all"));
    button.addEventListener("click", () => {
      if (button.getAttribute("aria-pressed") === "true") return;
      for (const other of controls.children) other.setAttribute("aria-pressed", String(other === button));
      const visible = topic === "all" ? books : books.filter(book => book.topics?.includes(topic));
      list.replaceChildren(portalBooks(visible, "tech"));
    });
    controls.append(button);
  }
  const content = document.createDocumentFragment();
  content.append(controls, list);
  return content;
}

function blogRow(book) {
  const row = node("div", "promo-item-container");
  const availableShop = book.shops.find(offer => !offer.sold);
  const cover = availableShop ? linkTo(availableShop.url, true) : node("span");
  if (availableShop) cover.setAttribute("aria-label", book.title + "の購入先");
  const image = node("div", "promo-item-hyoshi");
  image.style.backgroundImage = 'url("' + new URL(book.cover, catalogUrl).href + '")';
  cover.append(image);
  const main = node("div", "promo-item-main");
  const title = node("div", "promo-item-title", book.title);
  const description = node("iframe", "promo-item-description");
  description.title = book.title + "の紹介";
  description.src = new URL(book.descriptionUrl, catalogUrl);
  const shops = node("div", "promo-item-shops");
  for (const offer of book.shops) shops.append(banner(offer));
  main.append(title, description, shops);
  row.dataset.genre = book.genre;
  row.append(cover, main);
  return row;
}

function currentReceiptTable(books, store) {
  const current = node("table", "table table-sm table-bordered current-receipts");
  const labels = current.createTHead().insertRow();
  for (const label of ["作品", "形態", "販売価格", "著者受取額"]) labels.append(node("th", "", label));
  const rows = current.createTBody();
  for (const book of books) {
    for (const shop of book.shops.filter(shop => shop.shop === store && !shop.sold)) {
      const prices = Object.entries(shop.prices ?? {});
      for (const [form, price] of prices.length ? prices : [["", null]]) {
        if (shop.soldOutFormats?.includes(form)) continue;
        if (form === "紙" && shop.paperPublisher === "NextPublishing") continue;
        const amount = shop.receipts?.[form];
        const row = rows.insertRow();
        for (const value of [book.title, [shop.variant, form].filter(Boolean).join(" "), price == null ? shop.caption : price.toLocaleString("ja-JP") + "円",
          amount == null ? "条件未確認" : amount.toLocaleString("ja-JP") + "円"]) row.insertCell().textContent = value;
      }
    }
  }
  return current;
}

function receiptTable(receipts, books) {
  const wrap = node("div", "receipt-sheet");
  wrap.append(node("h2", "", "BOOTHの著者受取額（現在の登録価格）"),
    node("p", "", "1商品を単独注文、BOOSTなしの場合。電子はダウンロード、紙・紙＋電子は倉庫発送として計算しています。印刷原価・振込手数料は含みません。"));
  wrap.append(currentReceiptTable(books, "booth"),
    node("h2", "", "Amazon.co.jpのKDPロイヤリティ（通常販売1冊の概算）"),
    node("p", "", "税込希望小売価格を基準とします。印刷コスト・電子版の適用条件が未登録の行は条件未確認と表示します。Kindle Unlimitedの既読収益は含みません。"),
    currentReceiptTable(books, "amazon"), node("h2", "", "参考：旧早見表（当時の頒価・手数料）"));
  const table = node("table", "table table-sm table-bordered");
  const columns = ["Booth", "とら", "メロン", "技術書典OM", "おもバザハンズ", "Amazon", "メロン完全版"];
  const head = table.createTHead().insertRow();
  for (const label of ["早見表（円）", ...columns]) head.append(node("th", "", label));
  for (const group of receipts.groups) {
    const body = table.createTBody();
    const title = node("th", "", group.title);
    title.colSpan = head.cells.length;
    body.insertRow().append(title);
    for (const format of new Set(group.offers.map(offer => offer.format))) {
      const offers = group.offers.filter(offer => offer.format === format);
      for (const [field, label] of [["price","基準頒価"],["printing","オンデマンド印刷代"],["amount","受取金額"]]) {
        if (field === "printing" && !offers.some(offer => offer.printing)) continue;
        const row = body.insertRow();
        row.append(node("th", "", format + label));
        for (const shop of columns) {
          const offer = offers.find(item => item.shop === shop);
          row.insertCell().textContent = String(offer?.[field] ?? "—") + (field === "amount" ? offer?.note ?? "" : "");
        }
      }
    }
  }
  wrap.append(table);
  for (const note of receipts.notes) wrap.append(node("p", "", note));
  return wrap;
}

async function render() {
  const roots = document.querySelectorAll("[data-js-catalog]");
  try {
    const response = await fetch(catalogUrl);
    if (!response.ok) throw new Error(String(response.status));
    const catalog = await response.json();
    for (const root of roots) {
      const kind = root.dataset.jsCatalog;
      if (kind === "margin") {
        root.replaceChildren(receiptTable(catalog.receipts, catalog.books.filter(book => book.language !== "en")));
      } else if (kind === "blog") {
        const content = document.createDocumentFragment();
        for (const [genre, title] of [["tech","技術書コーナー"],["eki","北海道の駅巡りコーナー"]]) {
          const books = catalog.books.filter(book => book.blog && book.genre === genre);
          if (books.length) content.append(node("p", "head2", title));
          books.forEach(book => content.append(blogRow(book)));
        }
        root.replaceChildren(content);
      } else {
        const books = catalog.books.filter(book => kind === "tech-en"
          ? book.genre === "tech" && book.language === "en" : book.genre === kind && book.language !== "en");
        books.sort((a,b) => b.published.localeCompare(a.published, "ja", {numeric:true}));
        root.replaceChildren(kind === "tech" ? techBooks(books) : portalBooks(books, kind));
      }
    }
  } catch (error) {
    console.error("Catalog load failed", error);
    for (const root of roots) {
      const link = linkTo("https://koshian2.booth.pm/", false);
      link.textContent = "BOOTHで本を見る";
      root.replaceChildren("書籍情報を取得できませんでした。", link);
    }
  }
}
render();
