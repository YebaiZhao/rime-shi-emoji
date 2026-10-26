from copy import deepcopy
import unittest
from shi_emoji.datafiles import resolve_layers, merged_data
from shi_emoji.export import runtime_source


class MergeTests(unittest.TestCase):
    def test_no_alias_bleed_or_source_mutation(self):
        source = [{"id":"shared", "phrases":["甲词", "乙词"], "emoji":["🐄"]}]
        original = deepcopy(source)
        lexical = [{"id":"literal", "phrases":["甲词"], "emoji":["🐮"]}]
        rules, audit = resolve_layers([("model",100,source),("lexical",200,lexical)])
        by_phrase = {r["phrases"][0]:r for r in rules}
        self.assertEqual(by_phrase["甲词"]["emoji"], ["🐮"])
        self.assertEqual(by_phrase["乙词"]["emoji"], ["🐄"])
        by_phrase["甲词"]["emoji"].append("🐂")
        self.assertEqual(source,original)
        self.assertEqual(by_phrase["乙词"]["emoji"], ["🐄"])
        self.assertTrue(audit["甲词"][1]["selected"])

    def test_expression_combos_do_not_escape_authorized_phrases(self):
        rules,audit=resolve_layers([
            ("curated",300,[{"id":"awesome","phrases":["牛逼"],"emoji":["🐂🍺"],"suffix":"🐂🍺"}]),
            ("model",100,[{"id":"cow","phrases":["奶牛"],"emoji":["🐄","🐂🍺"]}])])
        self.assertEqual(rules[0]["emoji"],["🐂🍺"])
        self.assertEqual(rules[1]["emoji"],["🐄"])
        self.assertEqual(audit["奶牛"][0]["original_emoji"],["🐄","🐂🍺"])

    def test_real_cow_entries_and_trace(self):
        data=merged_data('data/phrases.json')
        by_phrase={r['phrases'][0]:r for r in data['rules']}
        for phrase in ['牛','老牛','黄牛','奶牛','乳牛','公牛','母牛','牛头']:
            self.assertNotIn('🐂🍺',by_phrase[phrase]['emoji'])
            self.assertEqual(by_phrase[phrase]['mapping_source'],'lexical')
        self.assertEqual(by_phrase['牛逼']['suffix'],'🐂🍺')
        self.assertTrue(any('🐂🍺' in r['original_emoji'] for r in data['mapping_audit']['奶牛']))
        self.assertNotIn('mapping_audit',runtime_source(data))

    def test_manual_word_guard_survives_generated_guards(self):
        data=merged_data('data/phrases.json')
        self.assertIn('发展中国家',data['word_guards'])
        self.assertIn('开发票',data['word_guards'])

    def test_curated_combo_remains_explicitly_authorized(self):
        rules,_ = resolve_layers([
            ('curated',300,[{'id':'off','phrases':['下班'],'emoji':['🏃💨']},
                            {'id':'hurry','phrases':['快跑'],'emoji':['🏃💨'],'suffix':'🏃💨'}]),
            ('model',100,[{'id':'wrong','phrases':['跑车'],'emoji':['🏃💨']}])])
        self.assertEqual([r['phrases'][0] for r in rules], ['下班','快跑'])

    def test_resolution_is_repeatable_and_literal_wins_without_union(self):
        data=merged_data('data/phrases.json')
        self.assertEqual(data,merged_data('data/phrases.json'))
        rule=next(r for r in data['rules'] if r['phrases']==['公牛'])
        self.assertEqual(rule['emoji'],['🐂','🐮'])
