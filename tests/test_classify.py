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
            ("【ゴ魔乙 プレイ動画】 前夜祭スコアタ death 477,884,044点 ランクB", "8th前夜祭"),
        ]:
            tags = collect.make_tags(title, "")
            self.assertIn("スコア大会(イベント)", tags, title)
            self.assertIn(name, tags, title)
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

        doc = {"updated": "", "videos": [
            {"videoId": "a" * 11, "title": "アリスギアコラボ記念スコアタ 11.97億", "status": "確認済み",
             "tags": ["スコア大会", "スコア大会(イベント)", "手動タグ"]},
            {"videoId": "b" * 11, "title": "第580回スコア大会 HYCレーザーA", "status": "確認済み",
             "tags": ["スコア大会", "スコア大会(週末)", "第580回"]},
        ]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "videos.json"
            with mock.patch.object(event_name_report, "VIDEOS_PATH", path), \
                    mock.patch("sys.stdout"):
                event_name_report.apply(doc)
            saved = json.loads(path.read_text(encoding="utf-8"))
        event, weekend = saved["videos"]
        self.assertEqual(event["tags"], ["スコア大会", "スコア大会(イベント)", "手動タグ", "アリスギアコラボ"])
        self.assertEqual(event["status"], "確認済み")
        self.assertEqual(weekend["tags"], ["スコア大会", "スコア大会(週末)", "第580回"])


if __name__ == "__main__":
    unittest.main()
