# juicyscript-catalog

サークル「じゅ～しぃ～すくりぷと」の公式ポータルとWordPressの記事下で使う公開書籍マスター。現行トップから書籍13件・グッズ1件を取り込んでいます。

## ローカルで見る

Python 3.10以降の標準ライブラリで動きます。リポジトリのルートで実行します。

```sh
python scripts/preview.py
```

- ポータルは http://127.0.0.1:8765/
- 記事下は http://127.0.0.1:8765/blog.html
- 配信用JSONは http://127.0.0.1:8766/catalog.json

起動時にビルドします。データ変更後は別ターミナルで `python scripts/build.py` を実行し、画面を再読み込みします。

## データ構成

| パス | 内容 |
|---|---|
| `data/books/<id>.json` | 書誌情報、発行年月、ジャンル、掲載設定、販売先ごとの価格と販売状況 |
| `data/books/<id>.html` | ポータルと記事下で共用する紹介文 |
| `covers/<id>.jpg` | 公開用書影 |

データ形式の例は [書誌・販売先](data/examples/example.json) と [紹介文](data/examples/example.html) にあります。
ビルドすると `dist/` に配信用の `catalog.json`、画像、紹介文、JS、CSS が生成されます。

販売データの補足は[ショップ別の計算仕様](docs/shop-receipts.md)にまとめています。
