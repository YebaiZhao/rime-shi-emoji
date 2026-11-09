import json
from pathlib import Path
import unittest

from shi_emoji.tier_export import LEVEL, compile_rules, match_metadata_source, runtime_source


class TierExportTests(unittest.TestCase):
    def test_matching_metadata_matches_source(self):
        self.assertEqual(Path("rime/lua/shi_emoji/match_metadata.lua").read_text(),
                         match_metadata_source("data"))

    def test_core_relations_and_generated_artifact(self):
        rules = compile_rules("data")
        rows = [json.loads(line) for line in Path("data/relation_reviews.jsonl").read_text().splitlines()]
        entries = {(phrase, e[0].replace("\ufe0f", "")): e[1:]
                   for phrase, targets in rules.items() for e in targets}
        for row in rows:
            if row["content_gate"] != "normal":
                continue
            key = row["expression"], row["target"].replace("\ufe0f", "")
            if row["status"] != "approved":
                self.assertNotIn(key, entries)
                continue
            self.assertEqual(entries[key], [LEVEL[row["min_tier"]],
                row["scope_review"]["code"] == "W", row["target_spec"]["kind"] == "fixed_sequence"])
        self.assertEqual(Path("rime/lua/shi_emoji/tier_data.lua").read_text(), runtime_source(rules))
