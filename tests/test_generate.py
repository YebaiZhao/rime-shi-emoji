import unittest
from shi_emoji.generate import gate, materialize
from shi_emoji.match import Matcher


class ModelGatesTests(unittest.TestCase):
    def setUp(self):
        self.policy = {"min_score": .64, "min_margin": .025, "alternative_min_score": .6,
                       "alternative_max_drop": .065, "reject_queries": ["进行"], "overrides": {}}

    def test_low_score_and_ambiguity_are_not_forced_matches(self):
        self.assertEqual(gate("钓鱼", [{"score": .5}, {"score": .3}], self.policy, set()), "low_score")
        self.assertEqual(gate("钓鱼", [{"score": .8}, {"score": .79}], self.policy, set()), "ambiguous")

    def test_curated_mappings_remain_supervised(self):
        self.assertEqual(gate("牛逼", [], self.policy, {"牛逼"}), "curated")
        self.assertEqual(gate("真牛逼啊", [], self.policy, {"牛逼"}), "contains_curated")

    def test_only_accepted_predictions_become_rules(self):
        rows = [{"query": "钓鱼", "status": "accepted", "candidates": [
            {"emoji": "🎣", "score": .8}, {"emoji": "🐟", "score": .68}]}]
        rules = materialize(rows, self.policy)
        self.assertEqual(rules[0]["emoji"], ["🎣"])
        self.assertEqual(rules[0]["origin"], "model-thresholded")
        rows[0]["status"] = "low_score"
        self.assertEqual(materialize(rows, self.policy), [])

    def test_model_matches_do_not_displace_supervised_intents(self):
        matcher = Matcher({"negators": [], "boundaries": [], "rules": [
            {"id": "curated", "phrases": ["下班"], "emoji": ["🏃💨"]},
            {"id": "model", "phrases": ["办公室"], "emoji": ["🏢"], "priority": -1000}]})
        self.assertEqual(matcher.search("下班离开办公室")["candidates"][0]["emoji"], "🏃💨")
