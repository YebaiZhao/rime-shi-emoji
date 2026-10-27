import json
from pathlib import Path
import unittest
from shi_emoji.coverage import audit, normalize
from shi_emoji.datafiles import merged_data
from shi_emoji.match import Matcher


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(Path("data/emoji_inventory.json").read_text())
        cls.data = merged_data("data/phrases.json")
        cls.semantic_data = merged_data("data/phrases.json", include_traditional=False)
        cls.matcher = Matcher(cls.data)

    def test_inventory_and_all_base_entries(self):
        report = audit(self.rows, self.semantic_data)
        self.assertEqual(report["summary"]["inventory"], 3781)
        self.assertEqual(report["summary"]["base_emoji"], 1906)
        self.assertEqual(report["summary"]["zero_terms"], 0)
        self.assertEqual(report["summary"]["zero_primary"], 0)
        self.assertEqual(report, json.loads(Path("data/coverage_report.json").read_text()))
        for key, maximum in json.loads(Path("data/coverage_budget.json").read_text()).items():
            self.assertLessEqual(report["summary"][key], maximum, key)

    def test_flags_symbols_professions_and_associations(self):
        for term, emoji in [("德国", "🇩🇪"), ("德国国旗", "🇩🇪"), ("日本", "🇯🇵"),
                            ("三文鱼", "🍣"), ("飞人", "🕴️"), ("女科学家", "👩‍🔬"),
                            ("禁止使用手机", "📵"), ("蛋", "🥚"), ("山", "⛰️")]:
            with self.subTest(term=term):
                candidates = self.matcher.search(term, 100)["candidates"]
                self.assertIn(normalize(emoji), {normalize(r["emoji"]) for r in candidates})

    def test_country_names_prefer_their_flags(self):
        by_phrase={r['phrases'][0]:r for r in self.data['rules']}
        for row in self.rows:
            if row['skin_variant'] or row['subgroup']!='country-flag':
                continue
            for name in row['names']:
                country=name.removeprefix('旗: ').removeprefix('旗：')
                with self.subTest(country=country):
                    self.assertEqual(by_phrase[country]['emoji'][0],row['emoji'])

    def test_canonical_names_are_primary_not_incidental_associations(self):
        by_phrase={r['phrases'][0]:r for r in self.data['rules']}
        for term,emoji in [('美人鱼','🧜‍♀️'),('水牛','🐃'),('耗子','🐀'),
                           ('独木舟','🛶'),('多云','🌥️'),('雾','🌫️'),
                           ('圣诞树','🎄'),('墨镜','🕶️'),('皇冠','👑'),
                           ('欧元','💶'),('收件箱','📥'),('天秤座','♎'),
                           ('小老鼠','🐁'),('家鼠','🐁')]:
            with self.subTest(term=term):
                self.assertEqual(by_phrase[term]['emoji'][0],emoji)

    def test_single_character_does_not_match_inside_words(self):
        rules = [r for r in self.data["rules"] if r["phrases"] == ["蛋"]]
        matcher = Matcher({"rules": rules, "negators": [], "boundaries": []})
        self.assertTrue(matcher.search("蛋")["matches"])
        self.assertFalse(matcher.search("蛋糕")["matches"])

    def test_single_character_runtime_rules_are_reviewed(self):
        policy = json.loads(Path("data/short_term_policy.json").read_text())
        active = {rule["phrases"][0]: rule for rule in self.semantic_data["rules"]
                  if len(rule["phrases"][0]) == 1 and "\u3400" <= rule["phrases"][0] <= "\u9fff"}
        self.assertEqual(set(active), set(policy["standalone_single"]) | set(policy["contextual_single"]))
        for term, emoji in policy["standalone_single"].items():
            self.assertEqual(active[term]["emoji"], emoji)
            self.assertTrue(active[term]["exact_only"])
        for term, emoji in policy["contextual_single"].items():
            self.assertEqual(active[term]["emoji"], [emoji])
            self.assertEqual(active[term]["min_context_len"], 5)

    def test_skin_variants_remain_explicitly_out_of_baseline(self):
        self.assertTrue(any(r["skin_variant"] for r in self.rows))
        self.assertTrue(any(r["subgroup"] == "country-flag" for r in self.rows))
