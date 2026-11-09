"""Complete name-review accounting and honest separation from input validation."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from shi_emoji.natural_names import build_reviews
from shi_emoji.reachability import analyze, write_report
from tests.test_lua_filter import LUA_LIBRARY


class NaturalNameReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_reviews()
        cls.by_emoji = {r['emoji'].replace('️', ''): r for r in cls.rows}

    def test_all_remaining_items_and_previous_decisions_are_accounted_for(self):
        self.assertEqual([r['index'] for r in self.rows], list(range(1,1907)))
        self.assertEqual(len(self.by_emoji), 1906)
        self.assertEqual(sum(r['round']=='remaining_1891' for r in self.rows), 1891)
        self.assertEqual(sum(r['round']=='first_batch' for r in self.rows), 15)
        recorded = [json.loads(l) for l in Path('data/natural_name_review/reviews.jsonl').read_text().splitlines()]
        self.assertEqual(recorded, self.rows)
        for row in self.rows:
            self.assertTrue(row['names'])
            for name in row['names']:
                self.assertNotIn(name['term'], ('=', '@'))
                if row['round']=='remaining_1891':
                    self.assertEqual(name['runtime_action'], 'review_only')
        previous = json.loads(Path('data/common_entry_reviews.json').read_text())['entries']
        for prior in previous:
            for target in prior['targets']:
                names = self.by_emoji[target.replace('️', '')]['names']
                result = next(n for n in names if n['term']==prior['term'])
                self.assertEqual(result['rationale'], prior['rationale'])
                self.assertEqual(result['runtime_action'], prior['runtime_action'])

    def test_misleading_labels_are_not_kept_as_primary_names(self):
        for emoji, wrong, selected in [('🪮','发夹','梳子'), ('🪠','活塞','马桶搋子'),
                                        ('🦺','救生衣','安全背心'), ('🦙','美洲鸵','美洲驼'),
                                        ('🦕','蜥蜴类','长颈恐龙')]:
            names = {n['term'] for n in self.by_emoji[emoji]['names']}
            self.assertNotIn(wrong, names)
            self.assertIn(selected, names)

    def test_ambiguous_names_remain_shared_and_flag_sequences_distinct(self):
        for term, targets in [('缆车', ['🚠','🚡']), ('骆驼', ['🐪','🐫']),
                              ('恐龙', ['🦕','🦖']), ('红色圆圈',['⭕','🔴'])]:
            for target in targets:
                name = next(n for n in self.by_emoji[target]['names'] if n['term']==term)
                self.assertEqual(set(name['shared_with']), set(targets)-{target})
        england = self.rows[1903]
        self.assertNotEqual(england['emoji'], '🏴')
        self.assertTrue(any(ord(c)>0xE0000 for c in england['emoji']))
        self.assertIn('英格兰', {n['term'] for n in england['names']})
        self.assertNotIn('英国', {n['term'] for n in england['names']})

    @unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
    def test_full_lua_report_rebuild_never_promotes_native_evidence(self):
        report = analyze(natural_names=True)
        self.assertEqual(report['summary']['natural_name_reviewed_emoji'], 1906)
        self.assertEqual(report['summary']['zero_reviewed_name_general_entry'], 0)
        self.assertEqual(report['summary']['zero_reviewed_name_divergent_entry'], 0)
        self.assertEqual(report['summary']['native_pinyin_checked_terms'], 0)
        for row in report['entries']:
            self.assertNotIn('natural_name_unverified', row['gaps'])
            for p in row['probes']:
                for layer in ('pinyin_candidate','native_preview','native_commit'):
                    self.assertEqual(p[layer]['status'], 'unverified')
        with tempfile.TemporaryDirectory() as directory:
            write_report(report, Path(directory))
            for filename in ('entries.tsv','entries.jsonl.gz','summary.json','name-gaps.tsv'):
                expected = (Path('data/reachability/entry-repairs-262')/filename).read_bytes()
                actual = (Path(directory)/filename).read_bytes()
                if filename.endswith('.gz'):
                    expected, actual = gzip.decompress(expected), gzip.decompress(actual)
                self.assertEqual(actual, expected, filename)
