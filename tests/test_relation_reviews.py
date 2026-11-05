"""Whole-corpus checks for offline relation data; no claims about Lua output."""
import copy
import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    'relation_reviews', Path(__file__).resolve().parents[1] / 'scripts/relation_reviews.py')
reviews = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviews)


class RelationReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = reviews.read_lines(reviews.OUTPUT)

    def test_whole_corpus_and_rebuild(self):
        self.assertEqual(self.rows, reviews.rebuild_rows())
        result = reviews.check(self.rows)
        self.assertEqual(result['core_total'], 11937)
        self.assertEqual(result['normalization_conflicts'], 0)
        progress = reviews.read_json(reviews.PROGRESS)
        for key, value in result.items():
            self.assertEqual(progress[key], value, key)

    def reject_mutation(self, index, mutate):
        rows = copy.deepcopy(self.rows)
        mutate(rows[index - 1])
        with self.assertRaises(AssertionError):
            reviews.check(rows)

    def test_reject_normalization_conflict(self):
        self.reject_mutation(856, lambda r: r.update(min_tier='strict'))

    def test_reject_known_exclusion_promotion(self):
        rows = copy.deepcopy(self.rows)
        row = rows[8203]
        # Keep generic scope fields valid; the audit/regression decision must still reject this change.
        row.update(status='approved', min_tier='general')
        row['applicability'], row['scope_review'] = reviews.scope_fields(row, 'C', 'synthetic change to a known decision')
        with self.assertRaises(AssertionError):
            reviews.check(rows)

    def test_reject_wrong_source_pointer(self):
        self.reject_mutation(1, lambda r: r['sources'][0].update(rule_index=1))

    def test_reject_adult_gate_loss(self):
        index = next(r['core_index'] for r in self.rows if r['content_gate'] == 'adult')
        self.reject_mutation(index, lambda r: r.update(content_gate='normal'))

    def test_reject_blanket_sentence_authorization(self):
        self.reject_mutation(1, lambda r: r.update(applicability=['whole_token']))

    def test_reject_fixed_sequence_split(self):
        index = next(r['core_index'] for r in self.rows if r['target_spec']['kind'] == 'fixed_sequence')
        self.reject_mutation(index, lambda r: r['target_spec'].update(kind='single_emoji'))

    def test_reject_unearned_runtime_validation(self):
        self.reject_mutation(1, lambda r: r.update(runtime_validation='passed'))

    def test_pending_and_discussion_are_not_scope_authorizations(self):
        for row in self.rows:
            if row['semantic_review']['status'] in ('pending', 'needs_discussion'):
                self.assertEqual(row['applicability'], [])
                self.assertFalse(row['runtime_eligible'])
            if row['scope_review']['code'] == 'C':
                self.assertEqual(row['applicability'], ['whole_candidate'])
                self.assertEqual(row['scope_review']['sentence_authorization'], 'pending_stage_three')
                self.assertIsNone(row['scope_review']['context_disambiguation']['executable_predicate'])

    def test_all_sources_keep_their_queue_destination(self):
        queue = reviews.source_projection(self.rows)
        self.assertEqual(len(queue), 130820)
        noncore = [r for r in queue if r['core_index'] is None]
        self.assertEqual(len(noncore), 118883)
        self.assertTrue(all(r['semantic_status'] == 'pending' for r in noncore))
        self.assertEqual(queue, reviews.read_gzip(reviews.ROOT / 'data/relation_review_queue.jsonl.gz'))

    def test_discussion_resolution_covers_original_queue(self):
        originals = {r['id'] for r in reviews.read_lines(reviews.DATA / 'standard3_reviews.jsonl')
                     if r['after']['status'] == 'needs_discussion'}
        current = reviews.current_reviews()
        pending = {r['id'] for r in reviews.read_json(reviews.DATA / 'unresolved.json')}
        self.assertEqual(len(originals), 298)
        self.assertEqual(len(pending), 0)
        self.assertEqual(pending, {key for key in originals
                                   if current[key]['after']['status'] == 'needs_discussion'})
        self.assertTrue(all(current[key]['semantic_review'] == 'rechecked' for key in originals))


if __name__ == '__main__':
    unittest.main()
