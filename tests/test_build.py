import unittest
from shi_emoji.build import load_catalog, rank


class RankingTests(unittest.TestCase):
    def test_override_precedes_semantic_order_and_deduplicates(self):
        catalog = [{"emoji": "🤪"}, {"emoji": "🧠"}, {"emoji": "😵‍💫"}]
        self.assertEqual(rank([0.1, 0.9, 0.8], catalog, ["🤪", "🤪"], 3), ["🤪", "🧠", "😵‍💫"])

    def test_unknown_override_is_rejected(self):
        with self.assertRaises(ValueError):
            rank([1], [{"emoji": "🤪"}], ["🏖️"], 1)

    def test_catalog_is_valid(self):
        self.assertGreaterEqual(len(load_catalog("data/emoji.jsonl")), 20)


if __name__ == "__main__":
    unittest.main()
