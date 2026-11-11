"""All 262 targets, old relations, sentence scope, and preference regressions."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from shi_emoji.coverage import normalize
from shi_emoji.reachability import contains, lua_suffixes
from shi_emoji.tier_export import compile_entry_rules, compile_rules, entry_runtime_source
from tests.test_lua_filter import LUA_LIBRARY


class EntryRepairDataTests(unittest.TestCase):
    def test_manifest_is_exactly_the_262_reviewed_gaps(self):
        manifest = json.loads(Path('data/entry_repairs_262.json').read_text())
        path = Path('data/reachability/natural-name-review/entries.jsonl.gz')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest['baseline_report_sha256'])
        original = [json.loads(line) for line in gzip.decompress(path.read_bytes()).decode().splitlines()]
        gaps = [r for r in original if not any(p['natural_name']['status']=='reviewed'
                and p['lua']['general']['status']=='reachable' for p in r['probes'])]
        self.assertEqual(len(gaps), 262)
        self.assertEqual({r['emoji'] for r in gaps}, set(manifest['target_emoji']))
        missing_mapping = [r for r in gaps if not any(p['natural_name']['status']=='reviewed'
                           and p['lexicon']['tier_mapping'] for p in r['probes'])]
        self.assertEqual(len(missing_mapping), 258)
        expected = {(p['term'], normalize(r['emoji'])) for r in gaps for p in r['probes']
                    if p['natural_name']['status']=='reviewed'}
        actual = {(r['term'], normalize(t)) for r in manifest['entries'] for t in r['targets']}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 496)
        self.assertEqual(len(manifest['entries']), 495)

    def test_all_existing_exact_alternatives_and_tiers_are_retained(self):
        old = compile_rules('data')
        new = compile_entry_rules('data')
        reviews = json.loads(Path('data/strict_entry_reviews.json').read_text())['entries']
        promotions = {(term, normalize(row['target'])) for row in reviews
                      for term in [row['term'], *row.get('traditional', [])]}
        self.assertEqual(Path('rime/lua/shi_emoji/entry_data.lua').read_text(), entry_runtime_source(new))
        for term, rule in new.items():
            tiers = {normalize(target): tier for target, tier in rule['targets']}
            for target, tier, _, _ in old.get(term, []):
                key = normalize(target)
                self.assertEqual(tiers[key], 1 if (term, key) in promotions else tier, term)


@unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
class EntryRepairLuaTests(unittest.TestCase):
    def test_strict_names_and_traditional_forms_emit_in_both_tiers(self):
        entries = json.loads(Path('data/strict_entry_reviews.json').read_text())['entries']
        cases = [(term, row['target']) for row in entries
                 for term in [row['term'], *row.get('traditional', [])]]
        actual = lua_suffixes(sorted({term for term, _ in cases}), Path('rime/lua'))
        for term, target in cases:
            for tier in ('strict', 'general'):
                self.assertTrue(contains(actual[term][tier], target), (term, target, tier, actual[term]))

    def test_every_repaired_name_and_target_with_extension_on_and_off(self):
        manifest = json.loads(Path('data/entry_repairs_262.json').read_text())
        rows = manifest['entries'] + manifest['preservation_entries']
        for adult in (False, True):
            actual = lua_suffixes([r['term'] for r in rows], Path('rime/lua'),
                                  {'skin':'default', 'gender':'neutral', 'adult':adult})
            for row in rows:
                for target in row['targets']:
                    for tier in ('general', 'divergent'):
                        self.assertTrue(contains(actual[row['term']][tier], target),
                                        (adult, row['term'], target, tier, actual[row['term']][tier]))

    def test_whole_candidate_overlay_does_not_change_sentence_matching(self):
        terms = list(compile_entry_rules('data'))
        sentences = [template.format(term) for term in terms
                     for template in ('请查看{}的说明', '不是{}', '{}真的很特别')]
        current = lua_suffixes(sentences, Path('rime/lua'))
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)/'lua'
            shutil.copytree('rime/lua', runtime)
            (runtime/'shi_emoji/entry_data.lua').write_text(entry_runtime_source({}))
            self.assertEqual(lua_suffixes(sentences, runtime), current)
            # New general-only names must not silently become strict matches.
            before = lua_suffixes(terms, runtime)
        after = lua_suffixes(terms, Path('rime/lua'))
        for term, rule in compile_entry_rules('data').items():
            if rule['min_tier'] > 1:
                self.assertEqual(before[term]['strict'], after[term]['strict'], term)

    def test_explicit_elder_gender_wins_without_disabling_skin_preferences(self):
        cases = {'老头':'👴', '老爷爷':'👴', '爷爷':'👴',
                 '老奶奶':'👵', '奶奶':'👵', '老太太':'👵'}
        for gender in ('neutral', 'female', 'male'):
            for skin, tone in [('default',''), ('light','🏻'), ('medium_light','🏼'),
                               ('medium','🏽'), ('medium_dark','🏾'), ('dark','🏿')]:
                actual = lua_suffixes(list(cases)+['老人'], Path('rime/lua'), {'skin':skin,'gender':gender})
                for term, target in cases.items():
                    self.assertTrue(contains(actual[term]['general'], target+tone), (term, skin, gender, actual[term]))
                generic = {'neutral':'🧓','female':'👵','male':'👴'}[gender]+tone
                self.assertTrue(contains(actual['老人']['general'], generic))

    def test_ranking_and_reasonable_polysemy(self):
        terms = ['亲亲','亲吻','脸红','微笑','害羞的笑脸','禁止标志','缆车','骆驼','恐龙','红圈','滑雪板']
        actual = lua_suffixes(terms, Path('rime/lua'))
        for term, expected in {'亲亲':'😗 😘','亲吻':'😗 💏','脸红':'😳 ☺️',
                               '微笑':'🙂 ☺️','害羞的笑脸':'😊'}.items():
            self.assertEqual(actual[term]['general'], expected)
        for term, targets in {'禁止标志':['🚫','🈲'], '缆车':['🚠','🚡'], '骆驼':['🐪','🐫'],
                               '恐龙':['🦕','🦖'], '红圈':['⭕','🔴'], '滑雪板':['🎿','🏂']}.items():
            for target in targets:
                self.assertTrue(contains(actual[term]['general'], target), (term, target, actual[term]))
