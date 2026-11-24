const slot = document.querySelector("[data-js-blog-header]");
if (slot) {
  try {
    const response = await fetch(new URL("blog-header.json", import.meta.url), { cache: "no-cache" });
    if (!response.ok) throw new Error(String(response.status));
    const banner = await response.json();
    const img = new Image(1000, 150);
    img.alt = banner.title + " の購入ページへ";
    img.style.cssText = "display:block;width:100%;height:auto";
    img.src = new URL(banner.image, import.meta.url);
    await img.decode();
    const link = document.createElement("a");
    link.href = banner.url;
    link.append(img);
    slot.replaceChildren(link);
  } catch (error) {
    console.warn("ブログヘッダーを表示できません", error);
  }
}
