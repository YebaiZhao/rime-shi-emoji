import unittest

from shi_emoji.reverse_audit import analyze


class ReverseAuditTests(unittest.TestCase):
    def test_context_gate_is_not_counted_as_standalone_reachability(self):
        rows = [{"emoji": "🦆", "name_en": "duck", "group": "Animals & Nature",
                 "skin_variant": False, "names": ["鸭子"], "keywords": []}]
        data = {"rules": [{"id": "duck", "phrases": ["鸭子"], "emoji": ["🦆"],
                           "min_context_len": 5}], "word_guards": [],
                "negators": [], "boundaries": []}
        result = analyze(rows, data)
        self.assertEqual(result["summary"]["zero_lexical_terms"], 0)
        self.assertEqual(result["summary"]["zero_reachable"], 1)
        self.assertEqual(result["entries"][0]["blocked_by_length"], ["鸭子"])
        data["rules"][0].pop("min_context_len")
        self.assertEqual(analyze(rows, data)["entries"][0]["reachable_terms"], ["鸭子"])
