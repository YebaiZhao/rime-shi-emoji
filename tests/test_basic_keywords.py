"""Reviewed keyword regressions, not independent semantic-accuracy evidence."""
import json
from pathlib import Path
import unittest

from shi_emoji.coverage import normalize
from shi_emoji.datafiles import merged_data
from shi_emoji.match import Matcher
from tests import test_lua_filter as lua_filter

CASES = json.loads(Path('tests/fixtures/basic_keywords_116.json').read_text())['cases']
REASONABLE = [
    ('一锅食物', '🍲'), ('勾号符号', '✔️'), ('医护人员', '🧑‍⚕️'),
    ('卫兵', '💂'), ('厕所', '🚾'), ('叉号', '❌'), ('向上箭头', '⬆️'),
    ('头晕目眩', '🥴'), ('扬声器', '🔉'), ('老鼠', '🐁'),
    ('警察', '👮'), ('释然的表情', '😮‍💨'), ('钢笔', '🖋️'),
    ('闪亮的', '✨'), ('音符', '🎵'), ('头晕目眩', '💫'),
]


class BasicKeywordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = merged_data('data/phrases.json')
        cls.matcher = Matcher(cls.data)

    def test_all_116_reviewed_terms_are_reachable(self):
        self.assertEqual(len(CASES), 116)
        self.assertEqual(len({case['review_id'] for case in CASES}), 116)
        for case in CASES:
            with self.subTest(query=case['query']):
                actual = [normalize(row['emoji']) for row in self.matcher.search(case['query'])['candidates']]
                self.assertTrue(actual)
                exact = next(r for r in self.data['rules'] if r['phrases'] == [case['query']])
                self.assertEqual(normalize(exact['emoji'][0]), normalize(case['expected'][0]))
                self.assertTrue({normalize(e) for e in case['expected']} <= set(actual))

    def test_generic_terms_are_suppressed_not_specific_words(self):
        for text in ('两个', '兩個', '表情'):
            self.assertEqual(self.matcher.search(text)['matches'], [], text)
        for text in ('这两个文件需要整理', '兩個檔案需要整理', '这个表情真可爱',
                     '两个妈妈和儿子一家', '今天收到了两个生日蛋糕', '表情包里面有桃子'):
            with self.subTest(text=text):
                result = self.matcher.search(text)
                self.assertFalse({'两个', '兩個', '表情'} & {r['phrase'] for r in result['matches']})
                self.assertNotIn('‼️', [r['emoji'] for r in result['candidates']])
        self.assertIn('‼️', [r['emoji'] for r in self.matcher.search('双叹号')['candidates']])
        for term in ('两个', '表情'):
            offers = self.data['mapping_audit'][term]
            self.assertTrue(offers)
            self.assertTrue(all(not offer['selected'] and offer['policy_exclusion'] for offer in offers))

    def test_new_single_characters_do_not_match_inside_words(self):
        for word, emoji in [('脚', '🦶'), ('腿', '🦵')]:
            self.assertEqual(self.matcher.search(word)['candidates'][0]['emoji'], emoji)
        for text in ('后台脚本正在执行', '腿脚不方便'):
            self.assertFalse({'🦶', '🦵'} & {r['emoji'] for r in self.matcher.search(text)['candidates']})
        self.assertNotIn('🌙', [r['emoji'] for r in self.matcher.search('我去月牙泉旅行')['candidates']])

    @unittest.skipUnless(lua_filter.LUA_LIBRARY, 'Needs actual Lua')
    def test_all_116_have_final_lua_suffixes(self):
        body = ["local norm=function(s) return (s:gsub('️','')) end"]
        for case in CASES:
            query = json.dumps(case['query'], ensure_ascii=False)
            body.append('do local suffix=norm(filter.suffix(' + query + ',CONFIG) or "")')
            first = json.dumps(normalize(case['expected'][0]), ensure_ascii=False)
            body.append('assert(suffix:sub(1,#' + first + ')==' + first + ', ' + query + '..suffix)')
            for emoji in case['expected']:
                target = json.dumps(normalize(emoji), ensure_ascii=False)
                body.append('assert(suffix:find(' + target + ',1,true), ' + query + '..suffix)')
            body.append('end')
        lua_filter.LuaFilterTests().execute('\n'.join(body))

    @unittest.skipUnless(lua_filter.LUA_LIBRARY, 'Needs actual Lua')
    def test_reasonable_differences_are_preserved_in_final_output(self):
        self.assertEqual(len({query for query, _ in REASONABLE}), 15)
        body = ["local norm=function(s) return (s:gsub('️','')) end"]
        for query, target in REASONABLE + [('碰杯','🍻'), ('电池','🪫'), ('警车','🚔'),
                                          ('头骨','☠️'), ('丝带','🎗️'), ('满月','🌝')]:
            text, emoji = json.dumps(query, ensure_ascii=False), json.dumps(normalize(target), ensure_ascii=False)
            body.append('assert(norm(filter.suffix(' + text + ',CONFIG) or ""):find('
                        + emoji + ',1,true), ' + text + ')')
        body.append("assert(filter.suffix('向上箭头',CONFIG)=='⬆️')")
        body.append("assert(filter.suffix('音符',CONFIG)=='🎵')")
        lua_filter.LuaFilterTests().execute('\n'.join(body))

    @unittest.skipUnless(lua_filter.LUA_LIBRARY, 'Needs actual Lua')
    def test_generic_pollution_is_gone_in_final_output(self):
        lua_filter.LuaFilterTests().execute('''
          for _,text in ipairs({'这两个文件需要整理','两个妈妈和儿子一家','这个表情真可爱'}) do
            local suffix=filter.suffix(text,CONFIG) or ''
            assert(not suffix:find('‼️',1,true),text..suffix)
            assert(not suffix:find('🙎',1,true),text..suffix)
          end
          assert(filter.suffix('表情',CONFIG)==nil)
          assert(filter.suffix('两个',CONFIG)==nil)
          assert((filter.suffix('两个生日蛋糕',CONFIG) or ''):find('🎂',1,true))
          assert((filter.suffix('双叹号',CONFIG) or ''):find('‼️',1,true))
        ''')
