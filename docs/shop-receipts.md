# ショップ別著者受取金額

BOOTHは販売中の商品の登録価格から算出します。1商品・BOOSTなしで、電子はダウンロード、紙と紙＋電子は倉庫発送を想定します。サービス利用料は価格の5.6%＋45円、倉庫発送手数料は価格の2.5%＋25円で、それぞれ1円未満を切り上げます。無料ダウンロードは0円です。旧早見表は当時の条件を明記して別掲します。[サービス利用料](https://booth.pixiv.help/hc/ja/articles/115004576874)・[倉庫発送手数料](https://booth.pixiv.help/hc/ja/articles/49117259932697)

`data/receipt-examples.json` は既存の公開早見表の基準頒価・形態・注釈です。書籍カードの通常販売価格と早見表の基準頒価には実際に差があります。早見表の9件を元の条件で再現し、計算式のある48件をビルド時に計算します。旧表で手入力されていたKDP紙版3件は当時の印刷費から再計算し、残り6件は注釈付きの公表値です。[公開早見表](https://shikoan.com/#margin)

Amazon.co.jpのKDP欄は購入欄の税込希望小売価格を基準に、日本での通常販売1冊あたりを円単位で見積もります。Amazon販売先の `kdp.printing` はペーパーバック1冊の印刷費（円）、`kdp.ebookRate` は電子版の適用率（35または70）、`kdp.delivery` は70%時に控除するKDP表示の配信費（円）です。紙版の印刷費や対象価格帯の電子版の料率が未登録なら「条件未確認」と表示します。NextPublishing経由の紙版とKindle Unlimitedの既読収益は対象外です。[日本向けの税・価格](https://kdp.amazon.co.jp/ja_JP/help/topic/G201849770)・[紙版の計算](https://kdp.amazon.co.jp/ja_JP/help/topic/G201834330)・[電子版の計算](https://kdp.amazon.co.jp/ja_JP/help/topic/G200634500)

## 計算結果の確認

リポジトリのルートで `python scripts/test_receipts.py` を実行します。
