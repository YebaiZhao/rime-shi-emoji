import json
from pathlib import Path
import unittest
from shi_emoji.match import Matcher
from shi_emoji.wordguards import compile_guards


class WordGuardTests(unittest.TestCase):
    def test_positive_and_negative_corpus(self):
        matcher = Matcher.load("data/phrases.json")
        for case in json.loads(Path("data/matching_cases.json").read_text()):
            with self.subTest(text=case["text"]):
                actual = {r["emoji"] for r in matcher.search(case["text"], 100)["candidates"]}
                self.assertTrue(set(case.get("include", [])) <= actual, actual)
                self.assertFalse(set(case.get("exclude", [])) & actual, actual)

    def test_offline_compiler_filters_pos_and_proper_substrings(self):
        data = {"rules": [{"phrases": ["动车", "开发", "火锅"]}]}
        words = compile_guards(data, ["电动车 24 n", "开发票 3 n", "吃火锅 3 l",
                                     "动车 36 n", "开发中 1 n"])
        self.assertEqual(words, ["开发票", "电动车"])

    def test_guard_does_not_hide_equal_or_larger_match(self):
        matcher = Matcher({"negators": [], "boundaries": [], "word_guards": ["电动车"],
                           "rules": [{"id":"train", "phrases":["动车"], "emoji":["🚄"]},
                                     {"id":"electric", "phrases":["骑电动车"], "emoji":["🛵"]}]})
        self.assertEqual([r["emoji"] for r in matcher.search("骑电动车")["candidates"]], ["🛵"])
        self.assertEqual([r["emoji"] for r in matcher.search("坐动车")["candidates"]], ["🚄"])
