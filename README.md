# ゴ魔乙 動画索引

「ゴシックは魔法乙女」（ゴ魔乙）の YouTube プレイ動画を、カテゴリ・公開日・キーワードで検索できる非公式ファンサイト。GitHub Pages で公開し、対象チャンネルの新着動画を GitHub Actions で定期的に自動収集する。

**公開URL:** https://irregularprime-source.github.io/gomaotsu-videos/

## サイトでできること

- カテゴリタグでの絞り込み（複数選択・いずれかを含む動画を表示）
- 公開日の FROM〜TO 期間指定（JST の日単位）
- タイトル・チャンネル名・説明文・メモのキーワード検索
- 公開日の新しい順／古い順の並べ替え
- 動画が増えても重くならないよう 100 件ずつの段階描画（「もっと見る」）

## リポジトリ構成

```
docs/                 … GitHub Pages で公開される領域
  index.html          … 一覧サイト本体
  videos.json         … 動画データ（自動収集＋手動登録がここに溜まる）
  tags.json           … フィルタチップに出すタグの定義（名前・色・表示順）
data/
  channels.json       … 自動収集の対象チャンネルリスト
scripts/
  collect.py          … 定期収集スクリプト（Actions から実行）
  reclassify.py       … 既存データのタグを最新ルールで再計算する保守ツール
  serve_admin.py      … 管理ツールをローカルで開くための起動用サーバー
tools/
  admin.html          … ローカル専用の管理ツール（公開されない）
.github/workflows/
  collect.yml         … 自動収集のワークフロー
requirements.txt      … collect.py の依存（requests のみ）
```

## 自動収集の仕組み

`.github/workflows/collect.yml` が **6時間ごと（cron）** と **手動実行（Run workflow）** で `scripts/collect.py` を動かす。

1. `data/channels.json` の各チャンネルのアップロード動画（最新50件）を取得
   - チャンネルID `UC…` の先頭を `UU` に置換したアップロードプレイリストを直接叩く（1回=1クォータ）
2. `gomaOnly: true` のチャンネルは全動画、`false` のチャンネルはタイトル・説明文に
   ゴ魔乙判定語（`ゴ魔乙` / `ごまおつ` / `ゴシックは魔法乙女`）を含む動画のみ対象
3. タイトル・説明文からタグを自動分類し、`docs/videos.json` に**未登録の動画だけ**追記
   - 既存の `videoId` は手動修正を保護するためスキップ
4. 差分があれば `github-actions[bot]` がコミット＆プッシュ

**同時実行対策:** cron と手動が重なっても壊れないよう、`concurrency` で実行を直列化し、
push が他の更新と競合して弾かれた場合は `git pull --rebase` で最大5回リトライする。

**APIキー:** リポジトリの Settings → Secrets → Actions に `YOUTUBE_API_KEY` を登録しておく（コードには一切含めない）。

### 対象チャンネルの追加

`data/channels.json` の `channels` 配列に追記する。管理ツール（後述）の「チャンネル登録」タブを使うと、URL や @ハンドルから channelId と名前を自動取得できる。

```json
{ "channelId": "UC…（24文字）", "name": "チャンネル名", "gomaOnly": false }
```

- `gomaOnly: true` … そのチャンネルの動画をキーワード判定なしで全てゴ魔乙として収集
- `gomaOnly: false` … ゴ魔乙判定語を含む動画のみ収集

## タグの仕組み

タグは 2 種類に分かれる。

- **フィルタ用タグ**（`docs/tags.json` に定義）… サイト上部の絞り込みチップに出る。
  スコア大会(週末) / スコア大会(イベント) / エーテルスコア大会 / アリーナ /
  ギルドバトル / イベントステージ / メインストーリー / キワメタワー / 未分類
- **表示専用タグ**（定義不要）… `第580回` などの回数や、`○○限定` のイベント名。
  `tags.json` に無いタグはタグ名から自動採色され、カード上と検索にだけ現れる。
  今後いくつ増えてもフィルタチップが破綻しない設計。

自動分類のキーワード表は `scripts/collect.py` の `TAG_KEYWORDS`（付与順＝表示順）にある。
回数は正規表現 `第(\d+)回`、イベント名は `○○限定` の形のみ抽出する。

### フィルタ用タグを増やす

`docs/tags.json` の `tags` 配列に `{ "name": …, "color": … }` を追加するだけ（コード変更不要）。
配列の順序がそのまま表示順になる。管理ツールの「タグ管理」タブからも編集できる。

## 管理ツール（ローカル専用）

`tools/admin.html` は、未確認動画のレビューや手動登録を行う作業用ツール。静的サイトは
ファイルを書き込めないため、**編集結果を各 JSON にコピー／ダウンロードして手動でコミット**する
方式をとる。`docs/` の外に置いてあるので公開されない。

### 起動

```
python scripts/serve_admin.py
```

表示される `http://127.0.0.1:8000/tools/admin.html` をブラウザで開く（127.0.0.1 限定）。
環境変数 `YOUTUBE_API_KEY` があれば自動で読み込む（`/api/key` 経由。ディスクにも git にも保存しない）。
無い場合はツール上部にキーを貼り付ける（この端末のブラウザの localStorage にのみ保存）。

### タブ

| タブ | 内容 |
|---|---|
| ① 未確認レビュー | `status: 自動分類` の動画を一覧。タグの追加・削除、メモ編集、「確認済みにする」（個別／一括） |
| ② 動画登録 | URL・ID から動画メタを取得し、`source: manual` / `status: 確認済み` で追加 |
| ③ チャンネル登録 | URL・@ハンドル・ID から channelId と名前を取得し、`data/channels.json` に追加 |
| ④ タグ管理 | `docs/tags.json` を編集（色変更・並べ替え・追加・削除、使用件数の警告つき） |

### 保存の流れ

編集すると下部の保存バーに変更ファイルが並ぶ。**コピー**（エディタに貼り付けて保存）または
**ダウンロード**したうえで、下記の置き場所に反映してコミット／プッシュする。JSON の書式は
`collect.py` と同じ（`ensure_ascii=False, indent=2` + 末尾改行）で揃えてあり、差分は最小になる。

| ツール上の名前 | 置き場所 |
|---|---|
| `videos.json` | `docs/videos.json` |
| `channels.json` | `data/channels.json` |
| `tags.json` | `docs/tags.json` |

## 収集ルールを変えたとき（再分類）

`collect.py` のキーワード表や抽出ルールを更新したら、収集済みの自動分類データに新ルールを
反映するため `reclassify.py` を実行する。手動登録・確認済み（`status: 確認済み`）は上書きしない。

```
python scripts/reclassify.py --dry-run   # 変更予定だけ表示
python scripts/reclassify.py             # 実際に書き込む
```

## ローカルでの動作確認

`serve_admin.py` はリポジトリ直下を配信するので、サイト本体もこれで確認できる：

```
python scripts/serve_admin.py
# → http://127.0.0.1:8000/docs/index.html  … サイト
# → http://127.0.0.1:8000/tools/admin.html … 管理ツール
```

管理ツールが不要なら、サイトだけを見る簡易サーバーでもよい：

```
cd docs
python -m http.server 8000   # → http://localhost:8000
```

`index.html` をファイルとして直接開く（`file://`）と videos.json を読み込めないため、必ずサーバー経由で開く。

## データ形式

### docs/videos.json

```json
{
  "updated": "2026-07-20T13:27:27+09:00",
  "videos": [
    {
      "videoId": "動画URLの v= 以降11文字",
      "title": "動画タイトル",
      "channel": "チャンネル名",
      "description": "説明文（任意）",
      "publishedAt": "2026-07-17T05:51:43Z",
      "registeredAt": "2026-07-20T13:27:27+09:00",
      "source": "auto | manual",
      "tags": ["スコア大会(週末)", "第580回"],
      "status": "自動分類 | 確認済み",
      "note": ""
    }
  ]
}
```

- `publishedAt` … 動画の公開日時（一覧のソート・期間絞り込みの基準）
- `source` … `auto`（自動収集）／`manual`（手動登録）
- `status` … `自動分類`（未確認）／`確認済み`。自動収集直後は `自動分類`

### data/channels.json

```json
{
  "channels": [
    { "channelId": "UC…（24文字）", "name": "チャンネル名", "gomaOnly": false }
  ]
}
```

### docs/tags.json

```json
{
  "tags": [
    { "name": "スコア大会(週末)", "color": "#d9a441" }
  ]
}
```

## 初回セットアップ（参考）

1. 公開リポジトリを作成し、一式を push する
2. Settings → Pages → Source: **Deploy from a branch**、Branch: **main** ／ **/docs**
3. Settings → Secrets and variables → Actions に `YOUTUBE_API_KEY` を登録
4. 数分後 `https://<ユーザー名>.github.io/<リポジトリ名>/` で公開される
