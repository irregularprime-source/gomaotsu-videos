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

    def test_new_dictionary_names(self):
        self.assertIn("弾幕神", collect.make_tags("【ゴ魔乙 プレイ動画】弾幕神スコアタC 1.61億", ""))
        self.assertIn("むちむちポーク", collect.make_tags("【ゴ魔乙】むちポスコアタざっくりやって一番気になった箇所(最後)", ""))
        weekend = collect.make_tags("【ゴ魔乙 プレイ動画】 第525回 hard 131,618,685 ハイパーレーザー／△ドラグーン改 ランクS", "")
        self.assertIn("スコア大会(週末)", weekend)
        self.assertNotIn("ドラグーン", weekend)

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
