import json
from pathlib import Path
import unittest

from shi_emoji.datafiles import merged_data
from shi_emoji.tier_export import LEVEL, compile_rules, guard_index, match_metadata_source, runtime_source


class TierExportTests(unittest.TestCase):
    def test_matching_metadata_matches_source(self):
        self.assertEqual(Path("rime/lua/shi_emoji/match_metadata.lua").read_text(),
                         match_metadata_source("data"))

    def test_packed_guard_index_preserves_all_terminals(self):
        source = merged_data("data/phrases.json")
        expected = set(source["word_guards"])
        expected.update(phrase for phrase, relations in compile_rules("data").items()
                        if not any(relation[2] is True for relation in relations))
        offsets, edges = guard_index(expected)

        def offset(node):
            return int.from_bytes(offsets[node * 3:node * 3 + 3], "little")

        def terminals(node, prefix):
            first = offset(node)
            if first & 0x800000:
                yield prefix
            for i in range(first & 0x7fffff, offset(node + 1) & 0x7fffff):
                edge = int.from_bytes(edges[i * 5:i * 5 + 5], "little")
                yield from terminals(edge >> 21, prefix + chr(edge & 0x1fffff))

        self.assertEqual(set(terminals(0, "")), expected)

    def test_core_relations_and_generated_artifact(self):
        rows = [json.loads(line) for line in Path("data/relation_reviews.jsonl").read_text().splitlines()]
        decisions = {review["id"]: review["decision"]
                     for batch in Path("data/sentence_scope_review").glob("batch-[0-9][0-9][0-9].jsonl")
                     for line in batch.read_text().splitlines()
                     for review in [json.loads(line)]}
        entries = {}
        for gate, filename in (("normal", "tier_data.lua"), ("adult", "adult.lua")):
            rules = compile_rules("data", content_gate=gate)
            entries.update({(gate, phrase, e[0].replace("\ufe0f", "")): e[1:]
                            for phrase, targets in rules.items() for e in targets})
            self.assertEqual(Path("rime/lua/shi_emoji", filename).read_text(), runtime_source(rules))
        for row in rows:
            key = row["content_gate"], row["expression"], row["target"].replace("\ufe0f", "")
            if row["status"] != "approved":
                self.assertNotIn(key, entries)
                continue
            scope = "token" if decisions.get(row["id"]) == "whole_token" else row["scope_review"]["code"] == "W"
            self.assertEqual(entries[key], [LEVEL[row["min_tier"]], scope,
                                            row["target_spec"]["kind"] == "fixed_sequence"], key)
