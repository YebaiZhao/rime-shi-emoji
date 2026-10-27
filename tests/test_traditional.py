import json
from pathlib import Path
import unittest

from shi_emoji.datafiles import merged_data, traditional_source_sha256
from shi_emoji.match import Matcher
from shi_emoji.traditional import generate


class TraditionalAliasTests(unittest.TestCase):
    def test_generator_keeps_explicit_entries_and_converts_guards(self):
        data = {"rules": [
            {"id": "dev", "phrases": ["开发"], "emoji": ["🧑‍💻"], "exact_only": True},
            {"id": "shrimp", "phrases": ["虾仁"], "emoji": ["🦐"]},
            {"id": "shrimp-trad", "phrases": ["蝦仁"], "emoji": ["🍤"]}],
            "word_guards": ["开发票"], "negators": ["不喜欢"], "boundaries": ["不过"]}
        convert = lambda text: {"开发": "開發", "虾仁": "蝦仁", "开发票": "開發票",
                                "不喜欢": "不喜歡", "不过": "不過"}.get(text, text)
        artifact = generate(data, [convert])
        self.assertEqual(artifact["aliases"], {"開發": "开发"})
        self.assertEqual(artifact["word_guards"], ["開發票"])
        self.assertEqual(artifact["negators"], ["不喜歡"])
        self.assertEqual(artifact["boundaries"], ["不過"])

    def test_generator_rejects_semantic_collision(self):
        data = {"rules": [{"id": "a", "phrases": ["甲"], "emoji": ["🐄"]},
                          {"id": "b", "phrases": ["乙"], "emoji": ["🐂"]}],
                "word_guards": [], "negators": [], "boundaries": []}
        with self.assertRaisesRegex(ValueError, "conflicting meanings"):
            generate(data, [lambda _: "丙"])

    def test_committed_aliases_are_current_and_existing_mappings_win(self):
        base = merged_data("data/phrases.json", include_traditional=False)
        artifact = json.loads(Path("data/traditional_aliases.json").read_text())
        self.assertEqual(artifact["source_sha256"], traditional_source_sha256(base))
        self.assertGreater(len(artifact["aliases"]), 4000)
        augmented = merged_data("data/phrases.json")
        by_phrase = {rule["phrases"][0]: rule for rule in augmented["rules"]}
        self.assertEqual(by_phrase["蝦仁"]["mapping_source"], "curated")
        self.assertEqual(by_phrase["開發"]["emoji"], by_phrase["开发"]["emoji"])
        self.assertEqual(by_phrase["開發"]["exact_only"], by_phrase["开发"]["exact_only"])
        self.assertIn("開發票", augmented["word_guards"])
        self.assertIn("不過", augmented["boundaries"])

    def test_traditional_matching_and_protection(self):
        matcher = Matcher.load("data/phrases.json")
        def emojis(text):
            return [row["emoji"] for row in matcher.search(text)["candidates"]]
        for text, first in (("開發", "🧑‍💻"), ("德國", "🇩🇪"),
                            ("海邊", "🏖️"), ("蝦仁", "🦐"),
                            ("我不想去海邊但是想玩遊戲", "🎮")):
            with self.subTest(text=text):
                self.assertEqual(emojis(text)[0], first)
        for text in ("開發票", "房地產開發", "發展中國家"):
            with self.subTest(protected=text):
                self.assertNotIn("🧑‍💻", emojis(text))


if __name__ == "__main__":
    unittest.main()
