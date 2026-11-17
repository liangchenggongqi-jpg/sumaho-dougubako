# スマホ道具箱（楽天アフィリエイト自動サイト）

毎朝6時ごろに GitHub Actions が楽天市場APIから商品を取得し、ランキング・値下がりページを自動生成して GitHub Pages に公開します。サーバー代は0円です。

## できること
- テーマごとの人気ランキング（評価×レビュー件数のベイズ平均で並べ替え）
- 価格履歴を毎日記録し、「値下がり中の商品」ページを自動作成
- すべての商品リンクがあなたのアフィリエイトリンクになる
- PR表記（ステマ規制対応）・楽天クレジット表記・sitemap.xml を自動で出力

## セットアップ（初回だけ・約20分）

### 1. GitHub にリポジトリを作る
1. GitHub で新しいリポジトリ `sumaho-dougubako` を作る（Public）
2. このフォルダの中身をすべてアップロード（`.github` フォルダも忘れずに）
3. Settings → Pages → Source を **GitHub Actions** にする
4. 公開URLは `https://あなたのユーザー名.github.io/sumaho-dougubako/` になります

### 2. 楽天ウェブサービスでアプリ登録（2026年の新仕様）
1. https://webservice.rakuten.co.jp/ にログインして「アプリID発行」
2. アプリURL／許可するWebサイトに、手順1の公開URLを登録（**これがないと403エラー**）
3. 発行された **アプリケーションID（UUID形式）** と **アクセスキー** を控える
4. 楽天アフィリエイトIDも同じ画面で確認できます

### 3. GitHub に鍵を登録
Settings → Secrets and variables → Actions
- **Secrets** タブ：`RAKUTEN_APP_ID`、`RAKUTEN_ACCESS_KEY`、`RAKUTEN_AFFILIATE_ID`
- **Variables** タブ：`SITE_URL` に手順1の公開URL

### 4. config.json を書き換える
- `site_url` を公開URLに、`operator_name` をあなたの名前・屋号に
- `themes` でテーマを追加・変更（キーワード・説明文・選び方）

### 5. 初回実行
Actions タブ → daily-update → **Run workflow**。数分でサイトが公開されます。以後は毎日自動です。

### 6. Google に知らせる
Google Search Console に公開URLを登録し、`sitemap.xml` を送信します。

## 手元で試す
```
python fetch.py --demo   # APIなしでサンプルデータ
python build.py          # public/ にサイトを生成
```

## 収益を伸ばすコツ
- **自動生成だけのページは検索で評価されにくいです。** 各テーマの `guide`（選び方）を自分の言葉で厚くするのが一番効きます
- テーマは「〇〇 おすすめ」で検索されるものを選び、少しずつ増やす
- 値下がりページを X や恐竜チャンネルの概要欄から紹介する
- 価格・在庫は取得時点のもの、と明記済み。商品の効果を断定する文章は書かない

## うまく動かないとき
| エラー | 対処 |
|---|---|
| 403 / REFERRER | 楽天側の許可サイトURLと `SITE_URL` を完全一致させる |
| accessKey must be present | アクセスキーのSecret名を確認 |
| wrong_parameter | `config.json` の `api_version` を楽天の最新版に更新 |
| 429 | 自動で待って再試行します。テーマ数が多い場合は減らす |
