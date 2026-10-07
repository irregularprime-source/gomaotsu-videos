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
  app.js              … 一覧サイトの JS（CSP でインラインを禁止しているため別ファイル）
  videos.json         … 動画データ（自動収集[登録ch＋検索]＋手動登録がここに溜まる）
  tags.json           … フィルタチップに出すタグの定義（名前・色・表示順）
  sitemap.xml         … 検索エンジン向けサイトマップ（build_static.py が自動生成）
  googlec5a426f06dcfde4b.html … Google Search Console の所有権確認ファイル（消さない）
data/
  channels.json       … 自動収集の対象チャンネルリスト
scripts/
  collect.py          … 登録チャンネル収集スクリプト（Actions から実行）
  search_collect.py   … 検索収集スクリプト（Actions から実行）
  reclassify.py       … 既存データのタグを最新ルールで再計算する保守ツール
  build_static.py     … videos.json から index.html 内の静的索引と sitemap.xml を生成
  serve_admin.py      … 管理ツールをローカルで開くための起動用サーバー
tools/
  admin.html          … ローカル専用の管理ツール（公開されない）
.github/workflows/
  collect.yml         … 登録チャンネル収集のワークフロー（6時間ごと）
  search.yml          … 検索収集のワークフロー（1時間ごと）
.github/dependabot.yml … ワークフローで使う Actions の更新PRを週1回作る設定
requirements.txt      … collect.py の依存（requests のみ）
```

## 自動収集の仕組み

`.github/workflows/collect.yml` が **6時間ごと（cron）** と **手動実行（Run workflow）** で `scripts/collect.py` を動かす。

1. `data/channels.json` の各チャンネルのアップロード動画（最新50件）を取得
   - チャンネルID `UC…` の先頭を `UU` に置換したアップロードプレイリストを直接叩く（1回=1クォータ）
2. `gomaOnly: true` のチャンネルは全動画、`false` のチャンネルはタイトル・説明文に
   ゴ魔乙判定語（`ゴ魔乙` / `ごまおつ` / `ゴシックは魔法乙女` / `ゴマ乙`）を含む動画のみ対象
3. タイトル・説明文からタグを自動分類し、`docs/videos.json` に**未登録の動画だけ**追記
   - 既存の `videoId` は手動修正を保護するためスキップ
4. 差分があれば `scripts/build_static.py` で静的索引と sitemap.xml を作り直し（後述「検索エンジン・AIクローラー向けの静的索引」）、
   `github-actions[bot]` がコミット＆プッシュ（検索収集も同じ）

### 検索収集（search.yml）

`.github/workflows/search.yml` が **1時間ごと（cron）** と **手動実行（Run workflow）** で `scripts/search_collect.py` を動かす。登録チャンネルに入っていない投稿者の動画も拾うのが目的。

1. YouTube `search.list` でゴ魔乙判定語を横断検索（`type=video` / `order=date` / 既定は直近6時間ぶん。実行間隔1hに対しウィンドウを広めに取り、cron遅延時の取りこぼしを防ぐ）
2. ヒットした動画を `videos.list` で本メタ取得し、**タイトル**にゴ魔乙判定語を含むものだけ対象（説明文だけ一致するFF14型ノイズを弾く）
3. `docs/videos.json` の未登録 `videoId` だけを `source: "search"` / `status: "自動分類"` で追記（重複は videoId で排除。登録チャンネルもスキップしない）
4. すべて未確認で入るため、管理ツールのレビューで取捨選択する

過去分をさかのぼるときは `--after` / `--before` で公開期間を区切って少しずつ実行する（後述「過去動画の一括登録」）。

**同時実行対策:** cron と手動が重なっても壊れないよう、collect.yml と search.yml は**同じ `concurrency` グループ**で実行を直列化し（`docs/videos.json` の書き込みが衝突しない）、
push が他の更新と競合して弾かれた場合は `git pull --rebase` で最大5回リトライする。

**APIキー:** リポジトリの Settings → Secrets → Actions に `YOUTUBE_API_KEY` を登録しておく（コードには一切含めない）。

### 対象チャンネルの追加

`data/channels.json` の `channels` 配列に追記する。管理ツール（後述）の「チャンネル登録」タブを使うと、URL や @ハンドルから channelId と名前を自動取得できる。

```json
{ "channelId": "UC…（24文字）", "name": "チャンネル名", "gomaOnly": false }
```

- `gomaOnly: true` … そのチャンネルの動画をキーワード判定なしで全てゴ魔乙として収集
- `gomaOnly: false` … ゴ魔乙判定語を含む動画のみ収集

## 過去動画の一括登録（バックフィル）

定期収集は最新分しか拾わないため、過去動画は次の2経路で少しずつ登録する（いずれも巨大な差分になるためローカル実行推奨）。

- **登録チャンネルの過去分**: `python scripts/collect.py --backfill`
  各チャンネルのアップロードを `nextPageToken` で全件たどり、未登録分を `source: "auto"` で追記する。
- **検索でひっかかる過去分**（未登録投稿者を含む）: `python scripts/search_collect.py --after 2025-01-01 --before 2025-01-08`
  公開期間を区切って（1週間・1か月など）窓をずらしながら少しずつ実行する。レビュー負荷・ノイズ・API コストを平準化するため。

どちらも `--dry-run` で追加予定を確認してから実行する。件数が増えたら `docs/videos.json` のサイズを見て分割の要否を判断する。

## アクセス解析

公開サイトの PV と流入元（何から来たか＝リファラー）を把握するため、[GoatCounter](https://www.goatcounter.com/) を導入している。`docs/index.html` の `</body>` 直前に計測タグを1行埋め込むだけで、既存機能への影響はない。

- **Cookie を使わないため、同意バナー・プライバシーポリシーは不要**（この点を最優先に選定。GA4 は Cookie 同意が必要になるため不採用）
- 管理画面: https://irregular-prime.goatcounter.com/ （**Paths** で PV、**Referrals** で流入元を確認）
- 管理ツール `tools/admin.html` は非公開かつ自分専用のため計測タグを入れていない（数字を汚さないため）
- 計測スクリプトは中身が固定される版付きの `count.v5.js` を、改ざん検知（SRI の `integrity`）付きで読み込む。
  自動更新されないので、新機能が必要になったら [版の一覧](https://www.goatcounter.com/help/countjs-versions)
  にある新しい版の URL と `integrity` に差し替える

## 検索エンジン・AIクローラー向けの静的索引

一覧は `videos.json` を JS で描画するため、HTML そのものには動画が1件も書かれていない。Googlebot は JS を
実行するので読めるが、GPTBot / ClaudeBot / PerplexityBot などの AI クローラーは基本的に JS を実行せず空の
ページとして扱う。そこで `scripts/build_static.py` が同じ内容を HTML に直接書き出している（2026-09-05 導入）。

- **静的索引**: `docs/index.html` の `<!-- BUILD:STATIC:START … -->` 〜 `<!-- BUILD:STATIC:END -->` の間に、
  全動画の一覧（`docs/tags.json` の主要タグごとの見出し＋どれにも属さない「その他」）を差し込む。
  1本の動画は最も具体的なタグ1つの見出しにだけ載せる（親タグ「スコア大会」等に重複させると HTML が膨らむため。
  各行には全タグを書き出すので情報は失われない）。
  - マーカー間は毎回上書きされるので手で編集しない。**マーカー自体を消すと build_static.py がエラーで止まる**。
  - JS が動く環境では `<html>` に付く `js` クラスで隠し、通常のカード一覧を見せる。`videos.json` を読めなかったときは
    クラスを外して静的索引を見せ直す。
- **JSON-LD**: `CollectionPage` + `ItemList`（直近50件）の構造化データ。他人の YouTube 動画に `VideoObject` を
  付けるのは Google のガイドライン上リスクがあるため、「一覧ページ」としてのマークアップに留めている。
- **sitemap.xml**: トップページ1件のみ。`lastmod` は `videos.json` の `updated`。
- **メタ情報**: `<head>` に canonical / OGP / Twitter Card / title・description を設定済み（こちらは手書きで、自動生成ではない）。
- **作り直すタイミング**: 収集ワークフロー2つ（`videos.json` に差分があったとき）と `変更を保存する.bat` が自動で実行する。
  手で作り直すなら `python scripts/build_static.py`（変更が無ければ「変更なし」と表示されるだけ）。
- **Google Search Console**: 所有権確認ファイル `docs/googlec5a426f06dcfde4b.html` を置いて確認済み。
  サイトマップ送信・インデックス登録リクエストも 2026-09-05 に実施済み。このファイルを消すと所有権確認が外れる。
  効果は Search Console の「検索パフォーマンス」と「URL 検査」で見る（GoatCounter は JS で計測するため、
  クローラーの訪問は数えられない。人間の検索流入は Referrals で見える）。

## セキュリティ対策

| 対象 | 対策 | 変更するときの注意 |
|---|---|---|
| 公開サイト（`docs/index.html`） | `<meta>` で CSP を指定（GitHub Pages はレスポンスヘッダーを設定できないため）。スクリプトは自サイト（`app.js`）と GoatCounter だけ許可し、画像・フォント・通信先も使っているものに限定 | 新しい外部サービス（画像・フォント・API など）を使うときは CSP の該当項目に追加する。追加しないとブラウザに読み込みを拒否される |
| 〃 インラインスクリプト | 禁止。例外は `<head>` の `html.js` を付ける1行だけで、CSP にその1行の sha256 ハッシュを書いて許可している | この1行を書き換えたらハッシュも計算し直す。JS を足すときは `app.js` に書く |
| GitHub Actions | `actions/checkout` などはタグではなくコミット SHA で固定（タグの付け替えで中身が差し替わるのを防ぐ） | 更新は Dependabot が作るPRで受け取る。メジャー版の更新は挙動が変わり得るので、内容を確認してからマージする |
| 管理ツール用サーバー（`serve_admin.py`） | Host ヘッダーが `127.0.0.1:8000` / `localhost:8000` 以外の要求は 403 で拒否（DNS リバインディング対策。起動中に悪意あるサイトを開いても APIキーや手元ファイルを読まれない） | ブラウザでは必ず `127.0.0.1` か `localhost` の URL で開く |

## タグの仕組み

タグは 2 種類に分かれる。

- **フィルタ用タグ**（`docs/tags.json` に定義）… サイト上部の絞り込みチップに出る。
  スコア大会 / スコア大会(週末) / スコア大会(イベント) / エーテルスコア大会 /
  リアルスコア大会 / ギルドバトル(通常) / ギルドバトル(イベント) / アリーナ /
  イベントステージ / メインストーリー / キワメタワー / ゴシック道 / ガチャ / 未分類
- **表示専用タグ**（定義不要）… `第580回` などの回数、`○○限定` のイベント名、
  および `data/event_tags.json` の辞書に一致したイベント名（周年 / 特訓 / コラボ / 季節 等）。
  `tags.json` に無いタグはタグ名から自動採色され、カード上と検索にだけ現れる。
  今後いくつ増えてもフィルタチップが破綻しない設計。

自動分類のキーワード表は `scripts/collect.py`（`SCORE_MARKERS` / `EVENT_WORDS` /
`GUILD_NORMAL_MARKERS` / `SIMPLE_KEYWORDS`、付与順＝表示順）にある。回数は正規表現 `第(\d+)回` で
抽出。イベント名は `○○限定` 形を正規表現で自動抽出するほか、`data/event_tags.json` の辞書に一致した
名前を表示専用タグとして付与し、一致時はスコア大会(週末)→(イベント)へ昇格する（辞書はデータ編集だけで
拡張できる）。ギルドバトル(通常)は明示語（ギルドバトル/ギルバト）に加え、属性有利ローテ名
（旧/新/三 × 火水風光闇）と闘技場マップ名でも判定するが、**スコア大会が付いた動画には付けない**
（「新火鉢」等がスコア大会動画に一致しても誤爆させないためのガード）。

### フィルタ用タグを増やす

`docs/tags.json` の `tags` 配列に `{ "name": …, "color": … }` を追加するだけ（コード変更不要）。
配列の順序がそのまま表示順になる。管理ツールの「タグ管理」タブからも編集できる。

## 管理ツール（ローカル専用）

`tools/admin.html` は、動画のレビュー・タグ修正や手動登録を行う作業用ツール。静的サイトは
ファイルを書き込めないため、**編集結果を各 JSON にコピー／ダウンロードして手動でコミット**する
方式をとる。`docs/` の外に置いてあるので公開されない。

### 起動

いちばん簡単なのは、リポジトリ直下の **`管理ツールを開く.bat` をダブルクリック**する方法。
最新データの取得（git pull）→ サーバー起動 → ブラウザで管理ツールを自動オープン、までまとめて行う。

コマンドで起動する場合：

```
python scripts/serve_admin.py         # サーバーのみ
python scripts/serve_admin.py --open  # ブラウザも自動で開く
```

いずれも `http://127.0.0.1:8000/tools/admin.html` をブラウザで開く（127.0.0.1 限定。
`127.0.0.1:8000` / `localhost:8000` 以外のホスト名で来た要求は拒否する。上の「セキュリティ対策」参照）。
環境変数 `YOUTUBE_API_KEY` があれば自動で読み込む（`/api/key` 経由。ディスクにも git にも保存しない）。
無い場合はツール上部にキーを貼り付ける（この端末のブラウザの localStorage にのみ保存）。

### タブ

| タブ | 内容 |
|---|---|
| ① レビュー・編集 | 動画を絞り込んで一覧。タグの追加・削除、メモ編集、確認済み↔未確認の切り替え（個別／一括）、一覧からの削除 |
| ② 動画登録 | URL・ID から動画メタを取得し、`source: manual` / `status: 確認済み` で追加 |
| ③ チャンネル登録 | URL・@ハンドル・ID から channelId と名前を取得し、`data/channels.json` に追加 |
| ④ タグ管理 | `docs/tags.json` を編集（色変更・並べ替え・追加・削除、使用件数の警告つき） |

### ①タブの絞り込み

件数が増えて全件スクロールが現実的でなくなったため、公開サイトと同じ操作感の絞り込みを備えている。
既定は「未確認のみ」で、状態を切り替えれば**確認済みの動画も後から修正できる**。

| 条件 | 内容 |
|---|---|
| キーワード | タイトル・チャンネル名・説明文・タグ・メモ・動画ID を対象（NFKC正規化＋小文字化で比較） |
| 確認状態 | 未確認のみ（既定）／確認済みのみ／すべて |
| タグ | `docs/tags.json` のタグをチップで複数選択（いずれかを含む）。件数は他の条件を反映した数 |
| チャンネル | 登録済み動画のチャンネル名から選択 |
| 公開日 | FROM〜TO（JST日単位。サイト側と同じ基準） |
| 並び順 | 公開日の新しい順／古い順 |

- 表示は50件ずつで、続きは「もっと見る」。
- チップに出るのは `docs/tags.json` に定義したタグのみ。`第581回` やイベント名などの自動タグは
  キーワード検索で引く（タグも検索対象に含めてある）。
- 「絞り込み結果をすべて確認済みにする」は**表示中の50件ではなく絞り込み結果の全件**が対象。
  件数を表示したうえで、もう一度クリックすると実行する。

### 動画を一覧から削除する

投稿者が動画を消すと、サイトにはサムネイルの出ないカードが残る。①タブの2つの機能で整理する。

**YouTube存在チェック**（ツールバーのボタン）
絞り込み結果の動画が YouTube に存在するかを API に問い合わせ、**見つからなかったものを一覧表示**する。
チェックボックス（既定ON）で選び、「選択した動画を videos.json から削除する」を2回クリックで削除。

- 対象は**現在の絞り込み結果**。全件を調べるなら「確認状態：すべて」＋条件クリアにしてから実行する。
- 動画IDを50件ずつまとめて問い合わせる（`videos.list`）。**1リクエスト＝1ユニット**なので、
  全2200件でも45ユニット程度（日次上限10,000）。
- 見つからない＝**削除・非公開・アカウント削除のいずれか**で、APIでは区別できない。
  限定公開（unlisted）は通常どおり返るため誤検出しない。

**一覧から削除**（各カードのボタン）
YouTube 側の状態に関係なく、その動画を `videos.json` から消す。誤収集（別ゲームの動画など）の除去用。
2回クリックで実行する。

> **注意**：削除するのは `videos.json` の1件だけで、YouTube 側には何もしない。
> このため、**YouTube に残っている動画を消しても、収集対象チャンネルの動画であれば次回の自動収集で再登録される**。
> 完全に除外したい場合は、`data/channels.json` からそのチャンネルを外すか、
> `collect.py` のキーワード判定を見直すこと（除外リストの仕組みは持たせていない）。

削除も他の編集と同じく、保存バーから `videos.json` を保存して反映する。

### 保存の流れ

編集すると下部の保存バーに変更ファイルが並ぶ。**コピー**（エディタに貼り付けて保存）または
**ダウンロード**したうえで、下記の置き場所に反映してコミット／プッシュする。JSON の書式は
`collect.py` と同じ（`ensure_ascii=False, indent=2` + 末尾改行）で揃えてあり、差分は最小になる。

| ツール上の名前 | 置き場所 |
|---|---|
| `videos.json` | `docs/videos.json` |
| `channels.json` | `data/channels.json` |
| `tags.json` | `docs/tags.json` |

置き場所に反映したら、リポジトリ直下の **`変更を保存する.bat` をダブルクリック**すると、
`build_static.py` で静的索引（`docs/index.html`）と `docs/sitemap.xml` を作り直したうえで、上記3つのJSONと
あわせて commit → `git pull --rebase` → push まで自動で行いサイトへ反映する
（自動収集が同時に更新していても取りこぼさないよう rebase を挟む）。コマンド操作は不要。
Python が見つからないか `build_static.py` が失敗したときは、そこで止めて commit しない。

**`[中断]` と表示されたとき**は、その画面の内容をそのまま伝えて復旧を依頼する。
前回の rebase が競合で止まったままだったり `main` 以外にいる状態でコミットすると、
保存が push できない場所に積まれ続けてサイトに反映されなくなるため、
`.bat` は**そういう状態を見つけたら何もせず終了する**（編集内容はファイルに残るので失われない）。
`pull` や `push` に失敗したときも同様に、そこで止めて後続の処理は行わない。

## 収集ルールを変えたとき（再分類）

`collect.py` のキーワード表・抽出ルール、または `data/event_tags.json`（イベント名辞書）を
更新したら、収集済みの自動分類データに新ルールを反映するため `reclassify.py` を実行する。
手動登録・確認済み（`status: 確認済み`）は上書きしない。

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
      "source": "auto | manual | search",
      "tags": ["スコア大会(週末)", "第580回"],
      "status": "自動分類 | 確認済み",
      "note": ""
    }
  ]
}
```

- `publishedAt` … 動画の公開日時（一覧のソート・期間絞り込みの基準）
- `source` … `auto`（登録チャンネル収集）／`search`（検索収集）／`manual`（手動登録）
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
