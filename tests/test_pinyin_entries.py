"""Exhaustive review accounting, optional translator boundaries and native proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from shi_emoji.export import lua_value
from shi_emoji.pinyin_entries import compile_pinyin_entries, pinyin_source, validate_reviews
from shi_emoji.reachability import contains, lua_suffixes
from tests.test_lua_filter import LUA_LIBRARY, LuaFilterTests

DIRECTORY = Path('data/pinyin_entry_review')


class PinyinEntryTests(unittest.TestCase):
    def test_each_of_174_original_names_has_an_explicit_decision(self):
        reviews = validate_reviews()
        self.assertEqual(len(reviews), 174)
        queries = json.loads((DIRECTORY/'selected_queries.json').read_text())['entries']
        self.assertEqual(len(queries), 137)
        self.assertEqual({(r['selected_term'], t) for r in reviews for t in r['targets']},
                         {(r['term'], t) for r in queries for t in r['targets']})
        for row in queries:
            self.assertEqual(''.join(row['syllables']).lower(), row['pinyin'])
        self.assertEqual(Path('rime/lua/shi_emoji/pinyin_data.lua').read_text(),
                         pinyin_source(compile_pinyin_entries()))
        prior = json.loads((DIRECTORY/'supplement.json').read_text())['entries']
        strict = json.loads(Path('data/strict_entry_reviews.json').read_text())['entries']
        self.assertEqual({(key, term) for key, names in compile_pinyin_entries().items() for term in names},
                         {(row['pinyin'], row['term']) for row in prior + strict if 'pinyin' in row})

    def test_recorded_native_commits_cover_all_52_targets_and_174_decisions(self):
        report = json.loads((DIRECTORY/'selected_after_native.json').read_text())
        # The report captures one runtime revision; exercise current data
        # with the separate live Lua and native tests.
        self.assertEqual(hashlib.sha256((DIRECTORY/'selected_queries.json').read_bytes()).hexdigest(), report['input_sha256'])
        observed = {r['term']:r for r in report['entries']}
        self.assertEqual(len(observed), 137)
        for row in validate_reviews():
            result = observed[row['selected_term']]
            self.assertEqual(result['keys'], row['pinyin'])
            self.assertEqual(result['pinyin_candidate']['status'], 'found', row['original_term'])
            self.assertTrue(result['preview_passed'] and result['commit_passed'] and result['text_commit_passed'], row)
            self.assertEqual(result['commit'], result['suffix'])
            self.assertEqual(result['text_commit'], row['selected_term']+' '+result['suffix'])
            for target in row['targets']:
                self.assertTrue(contains(result['commit'], target), row)
        original = json.loads(Path('data/reachability/entry-repairs-262/native.json').read_text())
        targets = set(json.loads(Path('data/entry_repairs_262.json').read_text())['target_emoji'])
        previously_passed = {t for r in original['entries'] if r['commit_passed'] for t in r['targets']}
        missing = targets - previously_passed
        self.assertEqual(len(missing), 52)
        self.assertLessEqual(missing, {t for r in report['entries'] if r['commit_passed'] for t in r['targets']})

    @unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
    def test_all_selected_names_emit_in_general_and_divergent(self):
        rows = json.loads((DIRECTORY/'selected_queries.json').read_text())['entries']
        for adult in (False, True):
            actual = lua_suffixes([r['term'] for r in rows], Path('rime/lua'),
                                  {'skin':'default','gender':'neutral','adult':adult})
            for row in rows:
                for target in row['targets']:
                    for tier in ('general','divergent'):
                        self.assertTrue(contains(actual[row['term']][tier], target), (row, tier))

    @unittest.skipUnless(LUA_LIBRARY, 'Actual Lua required')
    def test_exact_full_pinyin_only_and_switch_boundaries(self):
        cases = [{'code':key,'names':names} for key,names in compile_pinyin_entries().items()]
        LuaFilterTests().execute("""
          local translator=require('shi_emoji.pinyin')
          local enabled,ascii=true,false
          local segment={start=0,_end=0,has_tag=function(_,tag) return tag=='abc' end}
          local ctx={input='',get_option=function(_,key)
            return (key=='shi_emoji' and enabled) or (key=='ascii_mode' and ascii)
          end}
          local env={engine={context=ctx}}
          local function translate(code,start,finish)
            output={};ctx.input=code;segment.start=start or 0;segment._end=finish or #code
            translator.func(code,segment,env)
            return output
          end
          for _,case in ipairs("""+lua_value(cases)+""") do
            for _,code in ipairs({case.code,case.code:sub(1,1).."'"..case.code:sub(2)}) do
              local rows=translate(code)
              assert(#rows==#case.names,code)
              for i,row in ipairs(rows) do
                assert(row.text==case.names[i] and row.type=='shi_emoji_name')
                assert(row.start==0 and row._end==#code)
              end
            end
            enabled=false;assert(#translate(case.code)==0);enabled=true
            ascii=true;assert(#translate(case.code)==0);ascii=false
            assert(#translate(case.code,1)==0)
            assert(#translate(case.code,0,#case.code-1)==0)
            assert(#translate('wo'..case.code)==0)
            assert(#translate(case.code..'ma')==0)
          end
          assert(#translate('nihao')==0)
        """)


@unittest.skipUnless(os.environ.get('RIME_PROBE_USER'), 'Needs isolated native profile')
class PinyinEntryNativeTests(unittest.TestCase):
    def test_optional_supplement_switches_plain_chinese_and_nonmatching_order(self):
        with tempfile.TemporaryDirectory(prefix='shi-pinyin-test-') as directory:
            profile = Path(directory)/'profile'
            subprocess.run([sys.executable,'scripts/prepare_wanxiang_probe.py', '--source',os.environ['RIME_PROBE_USER'],
                            '--output',str(profile),'--zero-key','--no-adult','--pinyin-entries'],
                           check=True,capture_output=True,text=True)

            def probe(user, keys, state='on', ascii_mode=False):
                cmd=[sys.executable,'scripts/rime_probe.py','--user',str(user),'--keys',keys,'--option-state',state]
                if ascii_mode: cmd.append('--ascii')
                return json.loads(subprocess.run(cmd,check=True,capture_output=True,text=True).stdout)

            names=lambda r:[c['text'] for c in r['candidates']]
            self.assertIn('酷标志',names(probe(profile,'kubiaozhi')))
            self.assertEqual(probe(profile,'kubiaozhi{space}')['commit'],'酷标志')
            self.assertEqual(probe(profile,'kubiaozhi0')['commit'],'酷标志 🆒')
            self.assertEqual(probe(profile,'kubiaozhi{Alt+0}')['commit'],'🆒')
            self.assertEqual(names(probe(profile,'kubiaozhi','off')),
                             names(probe(os.environ['RIME_PROBE_USER'],'kubiaozhi','off')))
            self.assertNotIn('酷标志',names(probe(profile,'kubiaozhi',ascii_mode=True)))
            for keys in ('nihao','wanshua','shijie','kubiaozhiwo'):
                self.assertEqual(names(probe(profile,keys)),names(probe(os.environ['RIME_PROBE_USER'],keys)),keys)
