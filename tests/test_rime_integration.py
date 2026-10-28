"""Opt-in native-menu and candidate-enhancement tests using an isolated Rime profile."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("RIME_PROBE_USER"), "Set RIME_PROBE_USER to an isolated probe fixture")
class RimeIntegrationTests(unittest.TestCase):
    def probe(self, keys, state="on", menu=False, ascii_mode=False):
        command = [sys.executable, "scripts/rime_probe.py", "--user", os.environ["RIME_PROBE_USER"],
                   "--keys", keys, "--option-state", state]
        if menu:
            command.append("--menu-toggle")
        if ascii_mode:
            command.append("--ascii")
        proc = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)

    def test_original_order_is_preserved_with_inline_preview(self):
        baseline = self.probe("wanshua", state="off")["candidates"]
        result = self.probe("wanshua")
        self.assertTrue(result["mode"])
        rows = result["candidates"]
        self.assertEqual([r["text"] for r in rows], [r["text"] for r in baseline])
        self.assertIn("🏖️ 🎮", rows[0]["comment"])

    def test_space_keeps_original_and_stays_enabled(self):
        result = self.probe("wanshua{space}")
        self.assertEqual(result["commit"], "玩耍")
        self.assertTrue(result["mode"])

    def test_option_return_commits_preview(self):
        result = self.probe("wanshua{Alt+Return}")
        self.assertEqual(result["commit"], "玩耍 🏖️ 🎮")
        self.assertTrue(result["mode"])

    def test_continuous_input_stays_enabled(self):
        result = self.probe("wanshua{Alt+Return}haibian")
        self.assertEqual(result["commit"], "玩耍 🏖️ 🎮")
        self.assertEqual(result["candidates"][0]["text"], "海边")
        self.assertIn("🏖️", result["candidates"][0]["comment"])
        self.assertTrue(result["mode"])

    def test_selected_homophone_uses_its_own_preview(self):
        rows = self.probe("xiaren")["candidates"]
        self.assertEqual(rows[0]["text"], "吓人")
        self.assertEqual(rows[0]["comment"], "")
        self.assertEqual(rows[2]["text"], "虾仁")
        self.assertEqual(rows[2]["comment"], "")
        selected = self.probe("xiaren{Down}{Down}")["candidates"]
        self.assertEqual(selected[0]["comment"], "")
        self.assertIn("🦐 🍤", selected[2]["comment"])
        result = self.probe("xiaren{Down}{Down}{Alt+Return}")
        self.assertEqual(result["commit"], "虾仁 🦐 🍤")
        self.assertEqual(self.probe("xiaren3")["commit"], "虾仁")
        self.assertTrue(result["mode"])

    def test_experimental_slot_tracks_highlight_and_seventh_key(self):
        with tempfile.TemporaryDirectory(prefix="shi-emoji-slot-") as directory:
            profile = Path(directory) / "profile"
            subprocess.run([sys.executable, "scripts/prepare_wanxiang_probe.py", "--source",
                            os.environ["RIME_PROBE_USER"], "--output", str(profile),
                            "--candidate-slot"], check=True, capture_output=True, text=True)

            def probe(keys):
                result = subprocess.run([sys.executable, "scripts/rime_probe.py", "--user", str(profile),
                                         "--keys", keys, "--option-state", "on"],
                                        check=True, capture_output=True, text=True)
                return json.loads(result.stdout)

            rows = probe("xiaren")["candidates"]
            self.assertEqual([row["text"] for row in rows[:3]], ["吓人", "下人", "虾仁"])
            self.assertEqual(rows[6]["text"], "吓人")
            selected = probe("xiaren{Down}{Down}")
            self.assertEqual(selected["highlighted"], 2)
            self.assertEqual(selected["candidates"][6]["text"], "🦐 🍤")
            self.assertEqual(probe("xiaren{Down}{Down}7")["commit"], "🦐 🍤")
            self.assertEqual(probe("xiaren{space}")["commit"], "吓人")
            self.assertFalse(any("诗Emoji" in row["comment"] for row in probe("en")["candidates"]))

    def test_zero_key_defaults_to_text_and_emoji(self):
        with tempfile.TemporaryDirectory(prefix="shi-emoji-zero-") as directory:
            profile = Path(directory) / "profile"
            subprocess.run([sys.executable, "scripts/prepare_wanxiang_probe.py", "--source",
                            os.environ["RIME_PROBE_USER"], "--output", str(profile),
                            "--zero-key"], check=True, capture_output=True, text=True)

            def probe(keys, state="on"):
                result = subprocess.run([sys.executable, "scripts/rime_probe.py", "--user", str(profile),
                                         "--keys", keys, "--option-state", state],
                                        check=True, capture_output=True, text=True)
                return json.loads(result.stdout)

            rows = probe("xiaren")["candidates"]
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]["comment"], "")
            selected = probe("xiaren{Down}{Down}")
            self.assertIn("0 → 原文＋🦐 🍤", selected["candidates"][2]["comment"])
            self.assertEqual(probe("xiaren{Down}{Down}0")["commit"], "虾仁 🦐 🍤")
            self.assertEqual(probe("xiaren{space}")["commit"], "吓人")
            self.assertEqual(probe("hao")["candidates"][0]["comment"], "")
            self.assertEqual(probe("haoren")["candidates"][0]["comment"], "")
            ice = probe("bing{Down}{Down}")
            self.assertEqual(ice["candidates"][2]["text"], "冰")
            self.assertIn("0 → 原文＋🧊", ice["candidates"][2]["comment"])
            self.assertEqual(probe("bing{Down}{Down}0")["commit"], "冰 🧊")
            longer = probe("nizhenshiyigehaoren")
            self.assertEqual(longer["candidates"][0]["text"], "你真是一个好人")
            self.assertIn("0 → 原文＋🫵 🦸", longer["candidates"][0]["comment"])
            self.assertEqual(probe("nizhenshiyigehaoren0")["commit"], "你真是一个好人 🫵 🦸")
            self.assertEqual(probe("en0")["preedit"], "en⁴")
            self.assertEqual(probe("xiaren7")["commit"], "")
            self.assertEqual(probe("xiaren0", state="off")["commit"], "")
            self.assertFalse(any("诗Emoji" in row["comment"] for row in probe("en")["candidates"]))

    def test_zero_key_menu_switches_output_and_remembers_choice(self):
        with tempfile.TemporaryDirectory(prefix="shi-emoji-zero-menu-") as directory:
            profile = Path(directory) / "profile"
            subprocess.run([sys.executable, "scripts/prepare_wanxiang_probe.py", "--source",
                            os.environ["RIME_PROBE_USER"], "--output", str(profile),
                            "--zero-key"],
                           check=True, capture_output=True, text=True)

            def probe(keys, select=None):
                command = [sys.executable, "scripts/rime_probe.py", "--user", str(profile),
                           "--keys", keys, "--option-state", "on"]
                if select:
                    command += ["--menu-select", select]
                result = subprocess.run(command,
                                        check=True, capture_output=True, text=True)
                return json.loads(result.stdout)

            self.assertFalse(probe("xiaren")["emoji_only"])
            self.assertEqual(probe("xiaren{Down}{Down}0", "原文＋Emoji")["commit"], "🦐 🍤")
            selected = probe("xiaren{Down}{Down}")
            self.assertTrue(selected["emoji_only"])
            self.assertIn("0 → 🦐 🍤", selected["candidates"][2]["comment"])
            self.assertEqual(probe("xiaren{Down}{Down}0")["commit"], "🦐 🍤")
            self.assertEqual(probe("xiaren{Down}{Down}0", "仅Emoji")["commit"], "虾仁 🦐 🍤")
            self.assertFalse(probe("xiaren")["emoji_only"])
            self.assertEqual(probe("xiaren{Down}{Down}{Alt+Return}")["commit"], "虾仁 🦐 🍤")
            self.assertEqual(probe("xiaren{space}")["commit"], "吓人")
            self.assertEqual(probe("en0")["preedit"], "en⁴")

    def test_tab_remains_wanxiang_syllable_navigation(self):
        result = self.probe("xiaren{Down}{Down}{Tab}")
        self.assertEqual(result["commit"], "")
        self.assertTrue(result["candidates"])


    def test_escape_cancels_composition_not_setting(self):
        result = self.probe("wanshua{Escape}")
        self.assertTrue(result["mode"])
        self.assertEqual(result["commit"], "")
        self.assertEqual(result["candidates"], [])

    def test_unknown_list_is_unchanged(self):
        result = self.probe("en")
        baseline = self.probe("en", state="off")
        self.assertEqual(result["candidates"], baseline["candidates"])
        self.assertEqual(self.probe("en{space}")["commit"], "嗯")

    def test_negation_adds_emoji_instead_of_suppressing(self):
        result = self.probe("wobuxiangquhaibian")
        self.assertEqual(result["candidates"][0]["text"], "我不想去海边")
        self.assertIn("🙅 🏖️", result["candidates"][0]["comment"])
        self.assertEqual(self.probe("wobuxiangquhaibian{Alt+Return}")["commit"], "我不想去海边 🙅 🏖️")

    def test_contrast_does_not_negate_later_intent(self):
        result = self.probe("wobuxiangquhaibiandanshixiangwanyouxi")
        self.assertIn("🙅 🏖️ 🎮", result["candidates"][0]["comment"])

    def test_simple_negative_emotion_is_not_positive_recommendation(self):
        result = self.probe("wobukaixin")
        self.assertEqual(result["candidates"][0]["text"], "我不开心")
        self.assertIn("🙅 😄", result["candidates"][0]["comment"])

    def test_disabled_preserves_chinese(self):
        result = self.probe("wanshua", state="off")
        self.assertFalse(result["mode"])
        self.assertEqual(result["candidates"][0]["text"], "玩耍")
        self.assertNotIn("诗Emoji", str(result["candidates"]))

    def test_combo_candidate(self):
        result = self.probe("niubi")
        self.assertIn("🐂🍺", result["candidates"][0]["comment"])
        self.assertEqual(self.probe("niubi{Alt+Return}")["commit"], "牛逼 🐂🍺")

    def test_daily_work_phrase(self):
        self.assertEqual(self.probe("jintianyouyaojiaban{Alt+Return}")["commit"], "今天又要加班 💻☕")

    def test_reviewed_short_terms_show_in_highlighted_candidate(self):
        for keys, term, emoji in [("shangban", "上班", "💼"),
                                  ("waizuixiao", "歪嘴笑", "😏")]:
            with self.subTest(term=term):
                result = self.probe(keys)
                self.assertEqual(result["candidates"][0]["text"], term)
                self.assertIn(emoji, result["candidates"][0]["comment"])

    def test_generated_fishing_phrase(self):
        result = self.probe("zhoumoxiangqudiaoyu{Alt+Return}")
        self.assertTrue(result["commit"].startswith("周末想去钓鱼 "))
        self.assertIn("🎣", result["commit"])

    def test_country_flag_baseline(self):
        self.assertEqual(self.probe("deguo{Alt+Return}")["commit"], "德国 🇩🇪")

    def test_development_has_programmer(self):
        self.assertEqual(self.probe("kaifa{Alt+Return}")["commit"], "开发 🧑‍💻")

    def test_basic_punch_action_in_sentence(self):
        self.assertEqual(self.probe('wanshengjiebaodaxiaopengyou{Alt+Return}')['commit'], '万圣节暴打小朋友 🎃 👊 🧒')

    def test_electric_vehicle_is_not_train(self):
        self.assertEqual(self.probe("diandongche{Alt+Return}")["commit"], "电动车 🛵 🔋")

    def test_invoice_does_not_match_development(self):
        rows = self.probe("kaifapiao")["candidates"]
        self.assertEqual(rows[0]["text"], "开发票")
        self.assertFalse(any('🧑‍💻' in row['comment'] for row in rows))

    def test_food_association(self):
        self.assertEqual(self.probe("sanwenyu{Alt+Return}")["commit"], "三文鱼 🍣")

    def test_floating_person_alias(self):
        self.assertEqual(self.probe("feiren{Alt+Return}")["commit"], "飞人 🕴️")

    def test_ascii_does_not_disable_setting(self):
        result = self.probe("wanshua", ascii_mode=True)
        self.assertTrue(result["mode"])
        self.assertFalse(any("诗Emoji" in row["comment"] for row in result["candidates"]))

    def test_native_menu_remembers_both_states_across_restart(self):
        enabled = self.probe("wanshua", state="off", menu=True)
        self.assertTrue(enabled["mode"])
        restored = self.probe("wanshua", state="saved")
        self.assertTrue(restored["mode"])
        self.assertIn("🏖️ 🎮", restored["candidates"][0]["comment"])
        disabled = self.probe("wanshua", state="on", menu=True)
        self.assertFalse(disabled["mode"])
        restored = self.probe("wanshua", state="saved")
        self.assertFalse(restored["mode"])


if __name__ == "__main__":
    unittest.main()
