"""Whole-inventory engineering evidence; not a natural-language accuracy test."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from shi_emoji.reachability import contains, lua_suffixes
from shi_emoji.tier_export import compile_rules, runtime_source
from tests.test_lua_filter import LUA_LIBRARY


class CommonEntryTests(unittest.TestCase):
    def test_supplement_preserves_every_existing_relation_and_scope(self):
        before = compile_rules('data', include_common=False)
        after = compile_rules('data')
        for term, rows in before.items():
            for row in rows:
                self.assertIn(row, after[term], term)
        for row in json.loads(Path('data/common_entry_reviews.json').read_text())['entries']:
            if row['runtime_action'] != 'add':
                continue
            for target in row['targets']:
                self.assertIn([target, 1, False, False], after[row['term']])

    def test_exact_target_identity_not_zwj_or_fixed_sequence_components(self):
        self.assertFalse(contains('😶‍🌫️', '😶'))
        self.assertFalse(contains('👩‍🌾', '👩'))
        self.assertFalse(contains('🐂🍺', '🐂'))
        self.assertTrue(contains('⭕ 🔴', '⭕'))
        self.assertTrue(contains('✌', '✌️'))

    @unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
    def test_entire_first_batch_and_preserved_polysemy(self):
        cases = json.loads(Path('data/common_entry_reviews.json').read_text())['entries']
        actual = lua_suffixes([r['term'] for r in cases], Path('rime/lua'))
        for row in cases:
            if row['runtime_action'] != 'add':
                continue
            for target in row['targets']:
                for tier, suffix in actual[row['term']].items():
                    self.assertTrue(contains(suffix, target), (row['term'], tier, target, suffix))
        self.assertTrue(contains(actual['红圈']['general'], '🔴'))
        self.assertTrue(contains(actual['滑雪板']['general'], '🏂'))
        # "灰心" retains its pre-existing divergent association, not promoted
        # to a literal match just to make a color-heart entry look covered.
        self.assertFalse(contains(lua_suffixes(['灰心'], Path('rime/lua'))['灰心']['strict'], '🩶'))

    @unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
    def test_added_names_do_not_change_sentence_triggering(self):
        import shutil
        names = [r['term'] for r in json.loads(Path('data/common_entry_reviews.json').read_text())['entries']]
        sentences = ['请查看'+term+'的说明' for term in names]
        current = lua_suffixes(sentences, Path('rime/lua'))
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)/'lua'
            shutil.copytree('rime/lua', runtime)
            (runtime/'shi_emoji/tier_data.lua').write_text(runtime_source(compile_rules('data', include_common=False)))
            self.assertEqual(lua_suffixes(sentences, runtime), current)

        # Exhaustive structural check: no newly introduced guard may contain
        # an existing sentence-enabled term. Covers automatic traditional aliases.
        before = compile_rules('data', include_common=False)
        after = compile_rules('data')
        sentence_terms = [term for term, rows in before.items() if any(r[2] for r in rows)]
        for term in after.keys() - before.keys():
            self.assertFalse(any(part in term for part in sentence_terms), term)

    def test_first_batch_snapshot_keeps_its_denominator_and_native_provenance(self):
        # The runtime has since changed in another workstream. This is the
        # recorded first-batch snapshot, not evidence about today's native UI.
        # test_natural_names rebuilds the entire current 1906-item Lua report.
        native = json.loads(Path('data/reachability/native-first-batch.json').read_text())
        snapshot = json.loads(Path('data/reachability/current/summary.json').read_text())
        with gzip.open('data/reachability/current/entries.jsonl.gz', 'rt') as stream:
            entries = [json.loads(line) for line in stream]
        sources = snapshot['metadata']['sources_sha256']
        self.assertEqual(native['runtime_sha256'], sources['rime/lua/shi_emoji/tier_data.lua'])
        self.assertEqual(native['reviews_sha256'], sources['data/common_entry_reviews.json'])
        self.assertEqual(len(entries), 1906)
        self.assertEqual(len({r['emoji'] for r in entries}), 1906)
        self.assertTrue(all(r['probes'] for r in entries))
        for tier in ('strict', 'general', 'divergent'):
            self.assertEqual(sum(not r['reachable_terms'][tier] for r in entries),
                             snapshot['summary']['zero_'+tier+'_entry'])
