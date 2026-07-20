# ゴ魔乙 動画索引

「ゴシックは魔法乙女」（ゴ魔乙）のYouTubeプレイ動画を、カテゴリ・公開日・キーワードで検索できる一覧サイト。

## 構成

```
docs/
  index.html    … 一覧サイト本体（GitHub Pagesで公開される）
  videos.json   … 動画データ（当面はこれを直接編集して登録する）
data/
  channels.json … 自動収集の対象チャンネルリスト（Phase 2で使用）
scripts/        … 収集スクリプト（Phase 2で追加予定）
```

## 初回セットアップ（GitHub Pages公開まで）

1. GitHubで新しい公開リポジトリを作成する（例：`gomaotsu-videos`）
2. このフォルダの中身一式をリポジトリにpushする
3. リポジトリの Settings → Pages を開く
4. 「Build and deployment」で Source: **Deploy from a branch**、
   Branch: **main** ／ フォルダ: **/docs** を選んで Save
5. 数分後、`https://<ユーザー名>.github.io/gomaotsu-videos/` で公開される

## 動画の手動登録（Phase 1の運用）

`docs/videos.json` の `videos` 配列に以下の形式で追加してpushする。
GitHubのWeb画面上で直接編集してもよい。

```json
{
  "videoId": "動画URLの v= 以降11文字",
  "title": "動画タイトル",
  "channel": "チャンネル名",
  "description": "説明文（任意）",
  "publishedAt": "2026-07-18T21:00:00+09:00",
  "registeredAt": "2026-07-20T00:00:00+09:00",
  "source": "manual",
  "tags": ["スコア大会(週末)"],
  "status": "確認済み",
  "note": ""
}
```

- `publishedAt` は**動画の公開日**（一覧のソート基準）
- `tags` は複数指定可。使えるタグ：
  スコア大会(週末) / スコア大会(イベント) / エーテルスコア大会 / アリーナ /
  ギルドバトル / イベントステージ / メインストーリー / キワメタワー / 未分類
- `status` は `自動分類`（未確認）か `確認済み`
- 最初から入っているサンプルデータ（videoIdがSAMPLE〜のもの）は削除してよい

## ローカルでの動作確認

`index.html` をダブルクリックで開くと videos.json が読み込めない場合がある。
その場合は docs フォルダで簡易サーバーを起動する：

```
cd docs
python -m http.server 8000
```

ブラウザで http://localhost:8000 を開く。

## 今後の予定

- Phase 2：YouTube Data APIによる自動収集＋キーワード自動分類＋Issueフォーム手動登録
- Phase 3：過去動画の一括登録
- Phase 4：使用キャラ・編成タグ等の拡張
