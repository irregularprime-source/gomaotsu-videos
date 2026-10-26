"""Offline regression checks for automatic tagging and channel filtering."""
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import collect


SUBCATEGORIES = [
    "スコア大会(週末)", "スコア大会(イベント)", "スコア大会(リーグ)", "スコア大会(月間)",
    "エーテルスコア大会", "リアルスコア大会",
]


def subcategories(title):
    return [t for t in collect.make_tags(title, "") if t in SUBCATEGORIES]


class ScoreSubcategoryTests(unittest.TestCase):
    def assert_sub(self, title, expected):
        self.assertEqual(subcategories(title), [expected], title)

    def test_round_number_is_weekend(self):
        self.assert_sub("【ゴ魔乙 プレイ動画】 第590回スコア大会 hard 29,102,739点 ランクA3", "スコア大会(週末)")

    def test_weekend_words_are_weekend(self):
        self.assert_sub("ゴ魔乙 ドヨアタ練習", "スコア大会(週末)")
        self.assert_sub("【#ゴ魔乙】今週のドヨアタ反省会【ゴシックは魔法乙女】", "スコア大会(週末)")

    def test_score_without_weekend_evidence_is_event(self):
        self.assert_sub("【ゴ魔乙 プレイ動画】弾幕神スコアタC 1.76億（アイテム無し）", "スコア大会(イベント)")
        self.assert_sub("【ゴ魔乙プレイ動画】むちむちスコアタ", "スコア大会(イベント)")

    def test_explicit_event_words_are_event(self):
        self.assert_sub("8周年記念スコアタ 後半", "スコア大会(イベント)")

    def test_round_beats_event_dictionary(self):
        title = "【ゴ魔乙 プレイ動画】第580回スコア大会 hard 299.7M HYCレーザーA／アンドロメタ オ追設 ランク弩S"
        tags = collect.make_tags(title, "")
        self.assertEqual(subcategories(title), ["スコア大会(週末)"])
        self.assertNotIn("HYCレーザー", tags)

    def test_event_dictionary_tags_event_videos(self):
        tags = collect.make_tags("🥈【ゴ魔乙 プレイ動画】HYCレーザーCスコアタ 弩death 5162M ラララ ランク弩S", "")
        self.assertIn("スコア大会(イベント)", tags)
        self.assertIn("HYCレーザー", tags)

    def test_league(self):
        self.assert_sub("【ゴ魔乙 プレイ動画】 第16回リーグ 第16回リーグ準決勝 リーグ準決勝A easy 27,338,297点", "スコア大会(リーグ)")

    def test_monthly(self):
        self.assert_sub("【ゴ魔乙 プレイ動画】更なる高みへ1月 7.85億 火フェニックス", "スコア大会(月間)")
        self.assert_sub("【ゴ魔乙 プレイ動画】月間スコアタ8月 3.82億 闇ドリル", "スコア大会(月間)")
        self.assert_sub("さらなる高みへ 2月", "スコア大会(月間)")
        self.assert_sub("月間スコア大会 3月", "スコア大会(月間)")
        # 「○月スコアタ」も月間（2026-10-20〜）
        self.assert_sub("【ゴ魔乙 プレイ動画】1月スコアタ 804M ガンソード", "スコア大会(月間)")
        self.assert_sub("【ゴ魔乙ﾌﾟﾚｲ動画】20'3月ｽｺｱﾀdeathｱｲﾃﾑ使用366,849,203点 ランクS", "スコア大会(月間)")
        self.assert_sub("6月 スコアタ 9.6億【ゴ魔乙 プレイ動画】", "スコア大会(月間)")
        self.assert_sub("【ゴ魔乙 プレイ動画】 7月スコア大会 2.48億 ドーン スプ改", "スコア大会(月間)")

    def test_other_category_rounds_are_not_score(self):
        for title in [
            "【ゴ魔乙 プレイ動画】第44回裏ゴシック道 裏十段 16億【ゴシックは魔法乙女】",
            "【ゴ魔乙 プレイ動画】第34回ギルイベBoost:3部　hard 闇　204,291個",
            "[ゴ魔乙] アリーナバトル 第64回 (Death Match)",
        ]:
            self.assertEqual(subcategories(title), [], title)
            self.assertNotIn("スコア大会", collect.make_tags(title, ""), title)

    def test_counts_that_are_not_rounds(self):
        for title in [
            "【ゴ魔乙 プレイ動画】1日1回SPステージ",
            "ゴ魔乙　怨撃激難ステージ　98M 2回被弾T_T",
            "【ゴ魔乙 プレイ動画】 新火有利ブレイク 体感的に20回くらい当たって慌てふためいた動画",
        ]:
            self.assertEqual(subcategories(title), [], title)

    def test_event_names_without_score_word_are_event(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 ゴライコウ襲来！ death 506,831,013点　ハイパレ/ジーナ　ラバラ", "ゴライコウ襲来"),
            ("【ゴ魔乙プレイ動画】必ず死なすっ！！真セセリ 比較的お手軽撃破 黒天津風単騎", "必ず死なすっ"),
            ("【ゴ魔乙】煩悶・水 death", "煩悶"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertEqual(subcategories(title), ["スコア大会(イベント)"], title)
            self.assertIn(name, tags, title)

    def test_attack_words_are_event(self):
        self.assert_sub("[ゴ魔乙]07/25 イベアタちょっと回りましょう[プレイ動画]", "スコア大会(イベント)")
        self.assert_sub("ゴ魔乙 オンゲキコラボ記念アタ 闇アストラルゲート単騎 バララ 19.83億", "スコア大会(イベント)")
        self.assert_sub("【ゴ魔乙 プレイ動画】クリスマスアタ 3.14億 風ランサー＋テンペスト", "スコア大会(イベント)")

    def test_event_round_is_not_weekend(self):
        # イベントの開催回（回数の直後が辞書のイベント名）は週末にしない（2026-10-14 ユーザー指示）
        for title in [
            "【ゴ魔乙 プレイ動画】第2回 コンボブレイクスコアタ 1,603,331,211点 ランクS",
            "【ゴ魔乙 プレイ動画】第2回ｺﾝﾎﾞﾌﾞﾚｲｸｽｺｱﾀ 25億 ハイパービッグバン 特特範",
        ]:
            tags = collect.make_tags(title, "")
            self.assertEqual(subcategories(title), ["スコア大会(イベント)"], title)
            self.assertIn("コンボブレイクスコアタ", tags, title)
            self.assertNotIn("第2回", tags, title)
        # 回数のあとにイベント名以外が続く週末の動画は従来どおり
        self.assert_sub("【ゴ魔乙 プレイ動画】第580回スコア大会 HYCレーザーA", "スコア大会(週末)")

    def test_dictionary_names_added_2026_10_15(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 ｳｪﾃﾞｨﾝｸﾞ総合ｽｺｱﾀB death 744,201,219点 ランクS", "ウェディング総合"),
            ("【ゴ魔乙 プレイ動画】 鋳薔薇総合スコアタA hard 105,428,854点 ランクS", "鋳薔薇総合"),
            ("13.9億点→豪華客船スコアタ(前半)【ゴ魔乙プレイ動画】", "豪華客船"),
            ("優勝【#ゴ魔乙 プレイ動画】妖精王スコアタ 15.40億 ララバ", "妖精王"),
            ("【ゴ魔乙】【限定】ﾗｲｵｯﾄｶﾞﾝｽｺｱﾀ 412M ヘルパーのみアイテム無", "ライオットガンスコアタ"),
            ("【ゴ魔乙 プレイ動画】 ビッグバンｽｺｱﾀ death 123,562,266点 ランクC", "ビッグバンスコアタ"),
            ("【ゴ魔乙 プレイ動画】祝砲スコア death 181M ナデシコ", "祝砲スコアタ"),
            ("[ゴ魔乙]03/08 イベアタなガルドラスコアタやっていきます[プレイ動画]", "ガルドラスコアタ"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertNotIn("妖精", collect.make_tags("優勝【#ゴ魔乙 プレイ動画】妖精王スコアタ 15.40億 ララバ", ""))

    def test_limited_score_tag(self):
        # イベントの「○○限定」には ○○ と ○○限定スコアタ の両方。表記ゆれは寄せる（2026-10-16 ユーザー指示）
        tags = collect.make_tags("【ゴ魔乙 プレイ動画】縋憶限定スコアタ闇　death 257,026,039点", "")
        self.assertIn("縋憶", tags)
        self.assertIn("縋憶限定スコアタ", tags)
        self.assertIn("縋憶限定スコアタ", collect.make_tags("[ゴ魔乙]02/04 縋憶スコアタやってみましょう、ピカトリクスはガンガン攻める⁉[プレイ動画]", ""))
        for title, name in [
            ("【ゴ魔乙 プレイ動画】縋憶編限定スコアタ　7.79億　グリモワール固定", "縋憶"),
            ("[ゴ魔乙]11/25 ラナンちゃ限定スコアタ！サクサクっとミッション達成[プレイ動画]", "ラナン"),
            ("[ゴ魔乙]09/23 イベアタは希亡ショット限定⁉報酬使い魔使えますよ[プレイ動画]", "希亡ショット"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn(name, tags, title)
            self.assertIn(f"{name}限定スコアタ", tags, title)
        # 大蛇限定はスコアタの語が無くてもイベント
        tags = collect.make_tags("【ゴ魔乙 プレイ動画】 大蛇限定 death 875,559,749点 ランク弩S", "")
        self.assertIn("スコア大会(イベント)", tags)
        self.assertIn("大蛇限定スコアタ", tags)
        # 週末の動画の武器名「大蛇」には付けない
        self.assertNotIn("大蛇限定スコアタ", collect.make_tags("【ゴ魔乙】第579回スコア大会 99.28M ピカトリクス&大蛇　オ範爆", ""))
        # イベント以外の「○○限定」には付けない（属性限定は除外語でもある）
        self.assertNotIn("属性限定スコアタ", collect.make_tags("属性限定ガチャ", ""))

    def test_dictionary_names_added_2026_10_16(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 ごまおつｳｨｰｸｽｺｱﾀ normal 78,673,843点 ランク弩S", "ごまおつウィーク"),
            ("【ゴ魔乙 プレイ動画】 白ロリスコアタ hard 120,806,378点 ランク弩S", "白ロリ"),
            ("【ゴ魔乙 プレイ動画】 ロロデミースコアタ death 599,413,682点 ランク超S", "ロロデミー"),
            ("【ゴ魔乙 プレイ動画】雪まつりスコアタ 583M 光リヴァ/火クロブレ/ラ", "雪まつり"),
            ("【ゴ魔乙 プレイ動画】ゲッチュビームスコアタ 5611万 魔2873 ダ吸波", "ゲッチュビームスコアタ"),
        ]:
            self.assertIn(name, collect.make_tags(title, ""), title)
        self.assertNotIn("ヘルズバードスコアタ", collect.make_tags("【ゴ魔乙 プレイ動画】 第455回スコア大会 hard 97,094,074点 ランクA 風ヘルズバード単騎 爆ダ爆", ""))

    def test_dictionary_names_added_2026_10_17(self):
        for title, name in [
            ("【ゴ魔乙】バランス調整テストスコアタ 14.92億 水パイル", "テストスコアタ"),
            ("【ゴ魔乙 プレイ動画】 ｻﾊﾞｲﾊﾞﾙｽｺｱﾀ前半 hard 91,561,302点 ランクS", "サバイバル前半"),
            ("【ゴ魔乙 プレイ動画】サバイバルスコアタ後半 194M 火ィィソ/ドラバナ/吸波ラ", "サバイバル後半"),
            ("【ゴ魔乙 プレイ動画】マジカルゾーン体験スコアタ2 1026M 光ブリキ/ダララ", "マジカルゾーン体験"),
            ("【ゴ魔乙 プレイ動画】黄金の水スコアタ 104M ヘルパヘルギガ2/バラバ", "黄金の水"),
            ("【ゴ魔乙 プレイ動画】 ルシフェルスコアタ death 635,807,051点 吸ババ ランク弩S", "ルシフェルスコアタ"),
            ("【ゴ魔乙】和ｶﾌｪLOVE★魅せｽｺｱﾀ 62.6M ラブボン 範ラダ", "LOVE★魅せ"),
            ("【ゴ魔乙 プレイ動画】 6周年★ﾋﾞｷﾞﾅｰｽｺｱﾀ hard 3,997,314点 ランクF", "6周年★ビギナー"),
            ("【ゴ魔乙 プレイ動画】【0章】限定スコアタ 266M バレットストーム", "0章限定スコアタ"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertNotIn("サバイバル前半", collect.make_tags("【ゴ魔乙 プレイ動画】サバイバルスコアタ後半 194M", ""))

    def test_dictionary_names_added_2026_10_18(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】叛光スコアタ 807M Allラナン ドラバナ/コ設吸", "叛光"),
            ("【ゴ魔乙 プレイ動画】 エルフの森スコアタ easy 52,790,567点 ランク弩S", "エルフの森"),
            ("【ゴ魔乙】黒煌騎スコアタ 204,969,253点 ヘルパー", "黒煌騎"),
            ("【ゴ魔乙 プレイ動画】 ホタル狩りスコアタ hard 31,069,485点 ランク超S", "ホタル狩り"),
            ("【ゴ魔乙 プレイ動画】闇劫翼スコアタ 8025万 ヘルパツイストスピア/吸吸吸", "闇劫翼"),
            ("【ゴ魔乙 プレイ動画】水再臨スコアタ 195M レンタルリヴァイアサン/ラ吸ラ", "水再臨"),
            ("【ゴ魔乙 プレイ動画】黄金の風スコアタ 100M レンタルドドーン/ラララ", "黄金の風"),
            ("【ゴ魔乙ﾌﾟﾚｲ動画】ﾐﾙｷｰｽｺｱﾀhard宝6個確認用16,157,402点 ランクS", "ミルキースコアタ"),
            ("ﾊﾟｰﾃｨｽｺｱﾀhard39Mﾊﾙﾏｹﾞ&ｱｽﾃﾛ【ゴ魔乙ﾌﾟﾚｲ動画】39,181,809点 ランクS", "パーティスコアタ"),
            ("【ゴ魔乙 プレイ動画】昇華スコアタ 361M ガンバースト(2814)/バラ吸", "昇華スコアタ"),
            ("【ゴ魔乙 プレイ動画】 クリスマスコアタ normal 50,929,050点 ランク超S", "クリスマス"),
            ("【ゴ魔乙 プレイ動画】超乙女スコアタ 118M 光ブリキ/範波", "超乙女"),
            ("【ゴ魔乙 プレイ動画】 水源鞭スコアタ death 127,685,773点 ランク弩S", "水源鞭"),
            ("【ゴ魔乙 プレイ動画】 眷族スコアタ death 427,820,864点 ランク弩S", "眷族"),
            ("【ゴ魔乙 プレイ動画】眷属スコアタ 512M", "眷族"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)

    def test_dictionary_names_added_2026_10_19(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 光源弓スコアタ death 298,621,026点 ランクA", "光源弓"),
            ("【ゴ魔乙 プレイ動画】闇源牙スコアタ 421M ロザードキル/ララ", "闇源牙"),
            ("【ゴ魔乙 プレイ動画】 風源鎚スコアタ death 509,418,737点 ランク弩S", "風源鎚"),
            ("【ゴ魔乙 プレイ動画】 光亡スコアタ normal 96,489,274点 ランクS", "光亡"),
            ("【ゴ魔乙 プレイ動画】 火亡スコアタ normal 21,448,803点 ランク超S", "火亡"),
            ("【ゴ魔乙 プレイ動画】 死戦鎚スコアタ death 67,972,336点 ランクS", "死戦鎚"),
            ("【ゴ魔乙 プレイ動画】 精霊スコアタ normal 24,582,382点 ランク弩S", "精霊"),
            ("【ゴ魔乙】昏い森のスコアタ 35.5M バハテンペ サ設サ", "昏い森"),
            ("【ゴ魔乙 プレイ動画】這卵スコアタ 3392万 カルブリキ/範サ範", "這卵"),
            ("【ゴ魔乙 プレイ動画】 ロザリースコアタ death 461,306,194点 ランク弩S", "新年ロザリースコアタ"),
            ("【ゴ魔乙 プレイ動画】 プルメリアスコアタ 454M", "新年プルメリアスコアタ"),
            ("【ゴ魔乙 プレイ動画】 カトレアスコアタ 152M Δ 範追全", "新年カトレアスコアタ"),
            ("【ゴ魔乙 プレイ動画】ラナンスコアタ 305M ラナムート/インフェ/吸ララ", "新年ラナンスコアタ"),
            ("【ゴ魔乙 プレイ動画】 スフレスコアタ death 372,545,441点 ランク弩S", "新年スフレスコアタ"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        # 限定スコアタやクリスマスのキャラ別には新年の名前を付けない
        self.assertNotIn("新年ラナンスコアタ", collect.make_tags("【ゴ魔乙】ラナン限定スコアタ 13.45億 鏡雷 クロブレ", ""))
        self.assertNotIn("新年ロザリースコアタ", collect.make_tags("【ゴ魔乙 プレイ動画】Xmasスコアタ ロザリー death黒クロノス単騎 347M", ""))

    def test_dictionary_names_added_2026_10_20(self):
        for title, name in [
            ("【ゴ魔乙】太正浪漫スコアタ・甲   水ブリキ＋火ω  6.81億", "太正浪漫スコアタ・甲"),
            ("【ゴ魔乙 プレイ動画】太正浪漫スコアタ・乙 417万", "太正浪漫スコアタ・乙"),
            ("【ゴ魔乙 プレイ動画】 スポーツスコアタ-A death 186,070,584点 ランク超S", "スポーツスコアタ-A"),
            ("【ゴ魔乙 プレイ動画】 スポーツスコアタ-B normal 41,605,048点 ランク超S", "スポーツスコアタ-B"),
            ("【ゴ魔乙 プレイ動画】 スポーツスコアタ-C hard 24,069,418点 ランク超S", "スポーツスコアタ-C"),
            ("【ゴ魔乙 プレイ動画】 侵魔公スコアタ death 274,094,664点 ランクS", "侵魔公"),
            ("【ゴ魔乙 プレイ動画】 黒罪完結記念スコアタ hard 30,562,026点 ランクS", "黒罪完結記念"),
            ("【ゴ魔乙 プレイ動画】 お姫様スコアタ hard 33,259,863点 ランク超S", "お姫様スコアタ"),
            ("【ゴ魔乙】姫様メイドスコアタhard【ゴシックは魔法乙女】", "姫様メイド"),
            ("【ゴ魔乙 プレイ動画】祝エンジェルスコアタ 3298万 カレドーン/アンフェルノ/設ラコ", "エンジェルスコアタ"),
            ("【ゴ魔乙 プレイ動画】 異世界スコアタにょ death 309,432,668点 ランク超S", "異世界"),
            ("【ゴ魔乙 プレイ動画】カグラスコアタ 267M 光ジェノ/⊿/範吸吸", "カグラスコアタ"),
            ("【ゴ魔乙 プレイ動画】 サーカススコアタ hard 28,549,108点 ランク超S", "サーカス"),
            ("【ゴ魔乙 プレイ動画】 ものがたりスコアタ death 97,814,613点 ランク超S", "ものがたり"),
            ("【ゴ魔乙】スィーツスコアタステージ【ゴシックは魔法乙女】", "スゥイーツ"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertNotIn("太正浪漫スコアタ・乙", collect.make_tags("【ゴ魔乙】太正浪漫スコアタ・甲 6.81億", ""))
        self.assertNotIn("お姫様スコアタ", collect.make_tags("【ゴ魔乙】姫様メイドスコアタhard", ""))

    def test_dictionary_names_added_2026_10_21(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 闇の怠神スコアタ death 130,321,802点", "闇の怠神"),
            ("【ゴ魔乙 プレイ動画】 水の猛神スコアタ death 81,306,508点", "水の猛神"),
            ("【ゴ魔乙 プレイ動画】 レギュラースコアタ death 156,600,040点", "レギュラースコアタ"),
            ("【ゴ魔乙 プレイ動画】 スコアタ・乱戦 hard 16,931,784点", "乱戦"),
            ("【ゴ魔乙】お菓子をどうぞスコアタ: デモホマンは範囲の置き方がわからない312.5M（吸/範/ラ）", "お菓子"),
            ("お菓子をスコアタ。2.1億【ゴ魔乙 プレイ動画】", "お菓子"),
            ("【ゴ魔乙】 プル願スコアタ_D  4.27億", "プルメリアの願いスコアタ"),
            ("【ゴ魔乙 プレイ動画】 エスプスコアタ", "エスプガルーダ"),
            ("【ゴ魔乙 プレイ動画】 妖怪スコアタ フォトンレイ 適当なリハビリ", "妖怪夏祭り"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertIn("魔法騎士", collect.make_tags("【ゴ魔乙 プレイ動画】 魔法騎士スコアタ death 100M", ""))
        self.assertNotIn("魔法騎士", collect.make_tags("【ゴ魔乙 プレイ動画】魔法騎士ボーナス 2.16億", ""))

    def test_dictionary_names_added_2026_10_22(self):
        for title, name in [
            ("【ゴ魔乙】闇影の乙女スコアタ難 55.2M 闇ドーン+インフェルノ", "闇影の乙女"),
            ("【ゴ魔乙】光輝のスコアタ 1.13億", "光輝のスコアタ"),
            ("【ゴ魔乙】風嵐のスコアタ難 1.34億", "風嵐"),
            ("【ゴ魔乙】水氷のスコアタ 1.27億", "水氷"),
            ("【ゴシックは魔法乙女】水氷スコアタ　シザーズエッジ固定　範ララ　アイテム有り　106M", "水氷"),
            ("ごまおつ 火焔のスコアタ 55,523,295", "火焔"),
            ("【ゴ魔乙】授業スコアタ 1.68億 闇ドーン+クロブレ", "授業スコアタ"),
            ("【ゴ魔乙】ゼビウススコアタ易: 誰が風で行くかバーカ30.2M（特/範/範）", "ゼビウススコアタ"),
            ("【ゴ魔乙 プレイ動画】 物語スコアタ hard 3,271,918点", "物語スコアタ"),
            ("【ゴ魔乙 プレイ動画】BABYスコアタ 2.56億 風デモンズホーン", "BABYスコアタ"),
            ("【ゴ魔乙 プレイ動画】 クリアカードスコアタ hard 11,057,282点", "クリアカード"),
            ("【ゴ魔乙 プレイ動画】 プリンセススコアタ易 normal 15,203,721点", "プリンセススコアタ"),
            ("【ゴ魔乙 プレイ動画】 ナイトスコアタ難 hard 41,158,959点", "ナイトスコアタ"),
            ("【ゴ魔乙 プレイ動画】 シヌガ★ヨイスコアタ death 68,894,017点", "シヌガ★ヨイ"),
            ("【ゴ魔乙】 シヌガ☆ヨイスコアタ ステージ確認", "シヌガ★ヨイ"),
            ("【ゴ魔乙 プレイ動画】 シヌガヨイスコアタ 92.7M 吸ララ", "シヌガ★ヨイ"),
            ("ジャラスターは運ゲーなのか？【授業スコアタ】【ゴ魔乙】", "授業スコアタ"),
            ("【ゴ魔乙】UMRスコアタ 易【うまるちゃんRコラボ】", "うまる"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertIn("ジャラスタースコアタ", collect.make_tags("【ゴ魔乙】ジャラスタースコアタ hard 136M", ""))
        self.assertNotIn("ジャラスタースコアタ", collect.make_tags("【ゴ魔乙】授業スコアタ ジャラスター 1.6億", ""))
        self.assertNotIn("光輝のスコアタ", collect.make_tags("【ゴ魔乙 プレイ動画】光輝スコアタ 35M mk2 モルフォ 爆爆特", ""))
        self.assertNotIn("クリアカード", collect.make_tags("【ゴ魔乙 プレイ動画】 クリアカードボーナス death 105,390,393点", ""))

    def test_dictionary_names_added_2026_10_22_extra(self):
        for title, name in [
            ("【ゴ魔乙】激難スコアタに挑戦！hard", "激難スコアタに挑戦"),
            ("ゴシックは魔法乙女　激ムズスコアタに挑戦　司唱姫シャンルー", "激難スコアタに挑戦"),
            ("【ゴ魔乙】サイクロンスコアタ 2.3億", "サイクロンスコアタ"),
            ("【ゴ魔乙】バウンドスコアタ 10.6M", "バウンドスコアタ"),
            ("【ゴ魔乙】むちむちスコアタ：難 2.60億 風ドラドン+ワイバーン", "むちむちスコアタ"),
            ("【ゴ魔乙】ムチムチスコアタ(難)【デスモード】", "むちむちスコアタ"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)

    def test_dictionary_names_added_2026_10_23(self):
        for title, name in [
            ("【ゴ魔乙】打ち上げスコアタステージ【ゴシックは魔法乙女】", "打ち上げスコアタ"),
            ("ごまおつ　シンクロスコアタnormal　火DDP+水プラズマビーム", "シンクロスコアタ"),
            ("ゴシックは魔法乙女　舞踏会スコアタハード　翠歌姫スフレ", "舞踏会スコアタ"),
            ("【ゴ魔乙】白組スコアタ易: いつものサイクロンが戻って来た22M", "白組スコアタ"),
            ("【ゴ魔乙】紅組スコアタ・難 36.1M", "紅組スコアタ"),
            ("紅スコアタ_DDP_1608万【ゴ魔乙】", "紅組スコアタ"),
            ("【ゴ魔乙】虫姫さまふたりコラボスコアタBGM", "虫姫コラボ"),
            ("ゴ魔乙　メイドイベント　スコアタ　ドラゴンバーン", "姫様メイド"),
            ("【ゴ魔乙】 ダチュラの悪夢 ブラスターだけの世界 【イベントスコアタ】", "ダチュラの悪夢"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)

    def test_dictionary_names_added_2026_10_23_extra(self):
        for title, name in [
            ("【ゴ魔乙】１周年スコア大会上級ステージ【ゴシックは魔法乙女】", "1周年スコア大会"),
            ("ゴシックは魔法乙女　GW特別スコア大会　闇歌姫ロザリー", "GW特別スコア大会"),
            ("ゴ魔乙 20160504 GWスコアタ 15.1M DDP", "GW特別スコア大会"),
            ("【ゴ魔乙】制服コレクション　スコア大会：かかってこい！　hard バースト", "制服コレクション"),
            ("【ゴ魔乙】 狙われた花嫁たちスコア大会 地獄の結婚D 【自分メモ】", "狙われた花嫁たち"),
            ("【ゴ魔乙】 緑の暴風：スコアタ-ルチカの挑戦 【自分配置メモ】", "ルチカの挑戦"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        self.assertNotIn("1周年スコア大会", collect.make_tags("【ゴ魔乙】11周年記念スコアタ hard", ""))

    def test_dictionary_names_added_2026_10_24(self):
        for title, name in [
            ("ゴシックは魔法乙女　狂詩曲二幕スコアタ1/3", "乙女の狂詩曲"),
            ("ゴ魔乙 幻詩曲第一幕スコアタ450万", "乙女の狂詩曲"),
            ("【ゴ魔乙】双髪の逆襲:終焉 ボス前43m【スコアタ】", "双髪の逆襲"),
            ("【ゴ魔乙】激しき鎮魂歌スコアタ【ゴシックは魔法乙女】", "鎮魂歌"),
            ("【ゴ魔乙】イベント「楽園の終焉」death 懐かしの設置稼ぎ【スコアタ】", "楽園の一幕"),
            ("ゴシックは魔法乙女 2015/04/12 日曜スコアタ 206万", "日曜スコアタ"),
            ("ゴシックは魔法乙女 祝日スコア大会 2回目", "祝日スコア大会"),
            ("【 ゴ魔乙 】 スコアソウル ニードル編 3400万 【 death 】", "スコアソウル"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)

    def test_rules_added_2026_10_26(self):
        # 回数が後ろに付く・「スコア大会」の前に付く3桁、「土曜」は週末。「月刊スコアタ」は月間。
        for title in ["スコアタ250ダチュ杯 風鍋 サササ  25.5M【ゴ魔乙 プレイ動画】",
                      "スコアタ 302 ごまおつ",
                      "【ゴ魔乙 プレイ動画】182スコア大会 3.86億 カルミア",
                      "【109M】スコア大会438 早回しにがてな初心者のさくせん",
                      "【ゴ魔乙】土曜スコア大会 自己記録総括（2021/07 - 2022/06）"]:
            self.assert_sub(title, "スコア大会(週末)")
        self.assertIn("第250回", collect.make_tags("スコアタ250ダチュ杯 風鍋 サササ  25.5M", ""))
        self.assert_sub("月刊スコアタ12月号 Ｚ ラララ  747M【ゴ魔乙 プレイ動画】", "スコア大会(月間)")
        # 点数（「,」区切り・単位付き）は回数にしない
        self.assert_sub("【ゴ魔乙 プレイ動画】 闇の怠神スコアタ 187,247,891", "スコア大会(イベント)")
        self.assert_sub("【ゴ魔乙 プレイ動画】 黒空騎スコアタ  151M アイテム無し", "スコア大会(イベント)")

    def test_dictionary_names_added_2026_10_26(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】 スコアタ！怪獣娘！？ death 236M", "怪獣娘"),
            ("【ゴ魔乙 プレイ動画】 黒空騎スコアタ death 126,793,450", "黒空騎"),
            ("警察スコアタイベ1話 63.9M", "乙女署"),
            ("【ゴ魔乙】覚醒スコアタ", "覚醒スコアタ"),
            ("お手軽？リヴァイアサン9億参考✨スーチーパイコラボ記念スコアタ", "スーチーパイコラボ"),
            ("6周年前夜祭スコアタ 火ジャヴァ＆火サラダ", "6th前夜祭"),
            ("2016/03/14 絆地獄かよ！？ hard 29,654,004点 ヤツカさん スコアタ", "絆地獄かよ！？"),
            ("[ゴ魔乙]1/5 大往生総合スコアタ1週目 光リヴァワインダー716M", "怒首領蜂"),
            ("【ゴ魔乙 プレイ動画】 大正浪漫スコアタ・乙", "太正浪漫スコアタ・乙"),
            ("【ゴ魔乙 プレイ動画】 死線牙スコアタ242M デモホ", "死戦牙"),
            ("ｳｪﾃﾞｨﾝｸ総合ｽｺｱﾀB ボルテックス Hレラ", "ウェディング総合"),
            ("【ゴ魔乙ﾌﾟﾚｲ動画】護神ｽｺｱﾀB 1.17億", "風の護神"),
            ("【ゴ魔乙 プレイ動画】 乱戦スコアタ 1714万 確認用", "乱戦"),
            ("579M→鏡雷(ミズチ)特訓！スコアタ【ゴ魔乙プレイ動画】", "鏡雷特訓"),
            ("【ゴ魔乙】プル願DEATHスコアタ: 頑張らないデモホ", "プルメリアの願いスコアタ"),
            ("【ゴ魔乙 プレイ動画】 絆スコアタB 魔力2258のパターン", "絆地獄"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        # 「絆地獄かよ！？」には 絆地獄 を付けない（2026-10-26 ユーザー指示）
        self.assertNotIn("絆地獄", collect.make_tags("2016/03/14 絆地獄かよ！？ hard スコアタ", ""))

    def test_guild_event_markers_added_2026_10_23(self):
        # 実技試験・ギルドイベ・Gフェスタはギルドバトル(イベント)（2026-10-23 ユーザー指示）
        for title in ["【ゴ魔乙】水有利 第２回ギルド実技試験 117k",
                      "ゴ魔乙【第3回ギルドイベ光有利】リアラちゃんメインカンスト",
                      "【ゴ魔乙 ギルド】 第14回Gフェスタ 火有利 134,601ジュエル 2日目"]:
            tags = collect.make_tags(title, "")
            self.assertIn("ギルドバトル(イベント)", tags, title)
            self.assertNotIn("スコア大会", tags, title)

    def test_gacha_round_is_not_score(self):
        # 「ガチャに5回挑戦」の回数はスコア大会の回数にしない（2026-10-23 ユーザー承認）
        for title in ["【ゴシックは魔法乙女】魔法乙女のガチャに５回挑戦　相変わらず全くでないですな・・・。",
                      "【ゴ魔乙】入学おめでとう♥新学期ガチャ10連+1回"]:
            self.assertEqual(collect.make_tags(title, "")[0], "ガチャ", title)
        self.assertIn("スコア大会(週末)", collect.make_tags("[ごまおつ]9/26第538回スコア大会とシェアガチャります", ""))

    def test_guild_round_is_not_score(self):
        # ギルドの回数（第2回ギルド実技試験・第60回ギルバト）はスコア大会の回数にしない（2026-10-23 ユーザー承認）
        for title in ["【ゴ魔乙】水有利 第２回ギルド実技試験 117k",
                      "【ゴシックは魔法乙女】第60回ギルバト10月10日(火)",
                      "【ゴ魔乙】第9回実技試験闇有利ブレ 復習用じゃなしにネタだよ稼げなさすぎるステージだったｗ",
                      "ゴ魔乙【第3回ギルドイベ光有利】リアラちゃんメインカンスト"]:
            self.assertNotIn("スコア大会", collect.make_tags(title, ""), title)
        # スコア大会の語があれば従来どおり
        self.assertEqual(subcategories("【ゴ魔乙】第104回スコアタ ギルドの皆と 20M"), ["スコア大会(週末)"])

    def test_round_not_count_words(self):
        # 「被弾2回」「5回収」は回数ではない（2026-10-23 ユーザー承認）
        self.assertIsNone(collect.extract_round(collect.norm("ギルドバトル新風有利38→70(被弾2回)")))
        self.assertIsNone(collect.extract_round(collect.norm("ゴ魔乙 夏休み終B-2 death 猫５回収")))
        self.assertIsNone(collect.extract_round(collect.norm("スコアタ 被弾12回")))
        self.assertEqual(collect.extract_round(collect.norm("ゴ魔乙 551回 ドヨアタ")), 551)

    def test_real_words(self):
        # 第1回・第2回のリアルスコア大会（「団体戦」が無い書き方）もリアルにする（2026-10-22 ユーザー指示）
        for title in ["【ゴ魔乙】第1回リアルスコア大会用激難ステージ 予選 レンタル使い魔限定サポート無しカオスウィング",
                      "ゴ魔乙第一回リアルスコアタ用の激難ステージがクリアできない件について",
                      "【ゴ魔乙】公開リアルスコアタ death サイクロン2.86億",
                      "第1回ごまおつスコア大会 決勝ステージ体験 hard 10,249,788",
                      "【ゴ魔乙 プレイ動画】第2回ごまおつスコア大会予選 プル願デス 518M",
                      "【ネタ】【ゴ魔乙 プレイ動画】第4回リアアタ団体戦予選 0点 ノーアイテム ノーコンティニュー"]:
            self.assertIn("リアルスコア大会", subcategories(title), title)
        # 週末の根拠もあれば週末
        self.assertEqual(subcategories("[ごまおつ]11/23・リアルスコアタ見ながら546回ドヨアタ・ガチャなど作業配信[ゴシックは魔法乙女][Vtuber]"),
                         ["スコア大会(週末)"])
        # 「ラブリアル」「マテリアル」「バリアアタック」はリアルにしない
        self.assertNotIn("リアルスコア大会", collect.make_tags("【ゴ魔乙 プレイ動画】光有利3ブレイク バリアアタック8秒試し 120979/198810", ""))
        self.assertNotIn("リアルスコア大会", collect.make_tags("【ゴ魔乙 プレイ動画】 観光ボーナス normal ラブリアル稼ぎテスト", ""))

    def test_real_qualifier(self):
        # 団体戦予選はリアル＋イベント＋名前タグ。週末の根拠（3桁の回数・週末の語）もあれば週末だけ（2026-10-15 ユーザー指示）
        for title in ["【ゴ魔乙】団体戦予選160M",
                      "【ゴ魔乙 プレイ動画】第3回ごまおつスコア大会 団体戦予選 normal 154M"]:
            tags = collect.make_tags(title, "")
            self.assertEqual(subcategories(title), ["リアルスコア大会", "スコア大会(イベント)"], title)
            self.assertIn("団体戦予選", tags, title)
        self.assertIn("第3回", collect.make_tags("【ゴ魔乙 プレイ動画】第3回ごまおつスコア大会 団体戦予選 normal 154M", ""))
        weekend = "[ごまおつ]8/25団体戦予選第586回スコア大会予習ステージ攻略[ゴシックは魔法乙女][Vtuber]"
        self.assertEqual(subcategories(weekend), ["スコア大会(週末)"])
        self.assertNotIn("団体戦予選", collect.make_tags(weekend, ""))
        # 予選でない団体戦はリアルだけ（従来どおり）
        self.assert_sub("このままだと「思春期ヴィマナBOYZ」が #ごまおつ リアルスコア大会団体戦に出場してしまう件", "リアルスコア大会")

    def test_new_dictionary_names(self):
        self.assertIn("弾幕神", collect.make_tags("【ゴ魔乙 プレイ動画】弾幕神スコアタC 1.61億", ""))
        self.assertIn("むちむちポーク", collect.make_tags("【ゴ魔乙】むちポスコアタざっくりやって一番気になった箇所(最後)", ""))
        weekend = collect.make_tags("【ゴ魔乙 プレイ動画】 第525回 hard 131,618,685 ハイパーレーザー／△ドラグーン改 ランクS", "")
        self.assertIn("スコア大会(週末)", weekend)
        self.assertNotIn("ドラグーン", weekend)

    def test_dictionary_names_added_2026_10_12(self):
        for title, name in [
            ("【ゴ魔乙 プレイ動画】空の旅スコアタ 625M 火ピカトリ/ジナコレ/ララ", "空の旅"),
            ("【ゴ魔乙】ファントムスコアタ 4被弾", "ファントム"),
            ("【ゴ魔乙 プレイ動画】 黄金の光スコアタ death 575,201,468点 ランクS", "黄金の光"),
            ("【ゴ魔乙 プレイ動画】 サマー総合スコアタB easy 24,159,245点 ランク弩S", "サマー総合"),
            ("ゴシックは魔法乙女 始めたてスコアタ", "始めたて"),
            ("ゴ魔乙 初心者スコアタ29位（2025/12/12時点）", "初心者"),
            ("[ゴ魔乙]12/16 学園編最終日 急いで回って…あ、ウェッハスコアタ[プレイ動画]", "20thマダラ"),
            ("【ゴ魔乙 プレイ動画】マダラスコアタ death 472M", "20thマダラ"),
            ("【ゴ魔乙】オリジンスコアタ 598M ニードルプラズマレイ", "オリジンショット"),
            ("ゴ魔乙【プレイ動画】かならず死なす　真セセリあり無被弾ミッション全てクリア", "必ず死なすっ"),
            ("【ゴ魔乙 プレイ動画】弾幕五重奏スコアタ 273M デストロイヤー 魔力+850", "弾幕五重奏"),
            ("【ゴ魔乙 プレイ動画】乙女の契りスコアタ 634M 魔力+750 火鏡雷/ラ吸ラ", "乙女の契り"),
            ("【ゴ魔乙 プレイ動画】堕落ショットスコアタ 505M 火モルフォ/ラ吸ラ", "堕落ショット"),
            ("【ゴ魔乙 プレイ動画】 狂炎スコアタ hard 45,193,735点 ランク超S", "狂炎"),
            ("CBスコアタ2nd⭐️21億点パターン再現【ゴ魔乙 プレイ動画】 ｺﾝﾎﾞﾌﾞﾚｲｸｽｺｱﾀ death 20.3億点 ランク弩S", "コンボブレイクスコアタ"),
            ("【ゴ魔乙 プレイ動画】 ﾆﾙｳﾞｧｰﾅｽｺｱﾀ death 344,494,863点 ランク弩S", "ニルヴァーナスコアタ"),
            ("【ゴ魔乙 プレイ動画】 ケイブシュースコアタ hard 73,570,952点 ランクS", "ケイブシュースコアタ"),
            ("【ゴ魔乙 プレイ動画】グリフォンスコアタ death 422M ヘルパー/ラララ", "グリフォンスコアタ"),
            ("【ゴ魔乙 プレイ動画】8th前夜祭スコアタ death 1,117,643,315点 ハイパービッグバン ラ吸ラ", "8th前夜祭"),
            ("【ゴ魔乙 プレイ動画】 7th前夜祭スコアタ death 1,448,497,008点 ランクS", "7th前夜祭"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
        # 7th と 8th の前夜祭は別。番号なしの前夜祭スコアタには付けない（2026-10-21 ユーザー判断）
        self.assertNotIn("8th前夜祭", collect.make_tags("【ゴ魔乙 プレイ動画】 7th前夜祭スコアタ death 1,448,497,008点 ランクS", ""))
        self.assertNotIn("8th前夜祭", collect.make_tags("【ゴ魔乙 プレイ動画】 前夜祭スコアタ death 477,884,044点 ランクB", ""))
        # 一般語は「スコアタ」付きのときだけ
        self.assertNotIn("初心者", collect.make_tags("【ゴ魔乙】初心者向けスコアタ解説", ""))

    def test_gothic_march_is_guild_event(self):
        tags = collect.make_tags("【ゴ魔乙 プレイ動画】 ゴシックマーチ：3部 hard ブレイク 159,598ジュエル 風有利 #ごまおつ", "")
        self.assertEqual(tags, ["ギルドバトル(イベント)"])
        # 焼肉祭はユーザー判断で現時点では対象外
        self.assertEqual(collect.make_tags("むちむち焼肉祭：3食 金曜 光有利 100k→177k", ""), ["未分類"])

    def test_ether_has_priority(self):
        self.assert_sub("エーテルスコア大会 第3回", "エーテルスコア大会")


class RoundPatternTests(unittest.TestCase):
    def assert_round(self, title, expected):
        self.assertEqual(collect.extract_round(collect.norm(title)), expected, title)

    def test_round_without_kai(self):
        self.assert_round("【ゴ魔乙 プレイ動画】 第538 第hard 103,101,132 ハイパーレーザー／エッタフロラ", 538)
        self.assert_round("【ゴ魔乙】ドョアタ568 411M👷‍♀️安全第一👷", 568)
        self.assert_round("D568TSA、自己ベスト前5.11億点、シャイン/メガドリ【ゴ魔乙プレイ動画】", 568)
        self.assert_round("本戦482✱124M ハイパールドビレ ラ吸波【ゴ魔乙 プレイ動画】", 482)
        self.assert_round("【ゴ魔乙530 】新ヒバチ単騎", 530)

    def test_score_values_are_not_rounds(self):
        self.assert_round("ゴ魔乙 100万DL記念", None)
        self.assert_round("ゴ魔乙 492m 風シャインフレア", None)
        self.assert_round("第100億点チャレンジ", None)


class ChannelFilterTests(unittest.TestCase):
    def entry(self, title, description):
        return {"title": title, "description": description, "tags": collect.make_tags(title, description)}

    def test_title_keyword_is_target(self):
        self.assertTrue(collect.is_channel_target(self.entry("【ゴ魔乙】雑談", "")))

    def test_description_only_needs_classified_title(self):
        self.assertTrue(collect.is_channel_target(
            self.entry("第553回 24.5億 28位 剣気/咲夜", "ゴシックは魔法乙女(ごまおつ)")))

    def test_description_only_with_unclassified_title_is_rejected(self):
        self.assertFalse(collect.is_channel_target(
            self.entry("【FF14】ピルグリム・トラバースT1～T50ボス失敗【赤魔道士ソロ】", "#ゴ魔乙 #ごまおつ")))

    def test_no_keyword_is_rejected(self):
        self.assertFalse(collect.is_channel_target(self.entry("第553回 24.5億", "")))


class EventNameApplyTests(unittest.TestCase):
    def test_apply_only_adds_names_to_event_videos(self):
        import json
        import tempfile
        from unittest import mock
        import event_name_report
        import videos_store

        doc = {"updated": "", "videos": [
            {"videoId": "a" * 11, "title": "アリスギアコラボ記念スコアタ 11.97億", "status": "確認済み",
             "publishedAt": "2025-05-01T00:00:00Z", "tags": ["スコア大会", "スコア大会(イベント)", "手動タグ"]},
            {"videoId": "b" * 11, "title": "第580回スコア大会 HYCレーザーA", "status": "確認済み",
             "publishedAt": "2025-05-02T00:00:00Z", "tags": ["スコア大会", "スコア大会(週末)", "第580回"]},
        ]}
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(videos_store, "VIDEOS_DIR", Path(temp)), \
                    mock.patch("sys.stdout"):
                event_name_report.apply(doc)
            saved = json.loads((Path(temp) / "2025.json").read_text(encoding="utf-8"))
        event, weekend = saved["videos"]
        self.assertEqual(event["tags"], ["スコア大会", "スコア大会(イベント)", "手動タグ", "アリスギアコラボ"])
        self.assertEqual(event["status"], "確認済み")
        self.assertEqual(weekend["tags"], ["スコア大会", "スコア大会(週末)", "第580回"])


if __name__ == "__main__":
    unittest.main()
