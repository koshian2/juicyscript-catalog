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
  const caption = offer.caption ?? Object.entries(offer.prices).map(([kind, amount]) => kind + amount + "円").join("、");
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
    row.append(store);
    if (offer.caption) {
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
      } else cell.append(price.toLocaleString("ja-JP"), node("small", "", "円"));
    }
  }
  return table;
}

function portalBooks(books, genre) {
  const content = document.createDocumentFragment();
  const today = new Date();
  let lastHeading;
  for (const book of books) {
    const [year, month] = book.published.split("/").map(Number);
    const age = (today.getFullYear() - year) * 12 + today.getMonth() + 1 - month;
    const recent = age >= 0 && age <= 12;
    const heading = genre === "goods" ? (recent ? "新作" : "グッズ") : (recent ? "新刊" : "既刊");
    const article = node("article", "book");
    const cover = node("div", "cover-well");
    const coverLink = linkTo(book.shops[0].url, true);
    const image = node("img", "cover-image");
    image.src = new URL(book.cover, catalogUrl);
    image.alt = book.title + "の表紙";
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
      details.prepend(node("summary", "", "目次・紹介の続きを読む"));
      synopsis.append(details);
    }
    const purchase = node("div", "purchase");
    purchase.append(node("h3", "", "購入先・価格"), priceTable(book));
    copy.append(node("p", "issued", year + "年" + month + "月発行"), bookTitle(book), synopsis, purchase);
    article.append(cover, copy);
    content.append(article);
  }
  return content;
}
function blogRow(book) {
  const row = node("div", "promo-item-container");
  const cover = linkTo(book.shops[0].url, true);
  cover.setAttribute("aria-label", book.title + "の購入先");
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

function receiptTable(receipts) {
  const wrap = node("div", "receipt-sheet");
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
        root.replaceChildren(receiptTable(catalog.receipts));
      } else if (kind === "blog") {
        const content = document.createDocumentFragment();
        for (const [genre, title] of [["tech","技術書コーナー"],["eki","北海道の駅巡りコーナー"]]) {
          const books = catalog.books.filter(book => book.blog && book.genre === genre);
          if (books.length) content.append(node("p", "head2", title));
          books.forEach(book => content.append(blogRow(book)));
        }
        root.replaceChildren(content);
      } else {
        const books = catalog.books.filter(book => book.genre === kind);
        books.sort((a,b) => b.published.localeCompare(a.published, "ja", {numeric:true}));
        root.replaceChildren(portalBooks(books, kind));
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
