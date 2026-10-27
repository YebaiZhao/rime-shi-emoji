import json
from pathlib import Path
import unittest
from shi_emoji.preferences import variant_data
from shi_emoji.coverage import normalize
from shi_emoji.export import lua_value, runtime_source
from shi_emoji.match import Matcher
import test_lua_filter as lua_tests


class EdgyDictionaryTests(unittest.TestCase):
    def test_phrase_families_and_ordinary_contexts(self):
        data=json.loads(Path('data/adult_phrases.json').read_text())
        self.assertEqual((len(data['rules']),sum(len(r['phrases']) for r in data['rules'])),(39,140))
        matcher=Matcher(data)
        expected={
            '涩涩':'adult:flirty', '色色':'adult:flirty-short',
            '开车':'adult:innuendo-short',
            '老司机开车':'adult:innuendo', '少儿不宜':'adult:topic',
            '黄段子':'adult:dirty-jokes', '擦边直播':'adult:edgy-content',
            '色图':'adult:pictures-short', '为爱鼓掌':'adult:euphemism',
            '今晚去开房':'adult:hotel', '车震':'adult:car-romance',
            '一夜情':'adult:hookup', '绿帽子':'adult:green-hat',
            '地狱笑话':'adult:dark-joke', '坟头蹦迪':'adult:grave-dance',
            '阴间操作':'adult:underworld-meme', '血流成河':'adult:bloodbath',
            '头破血流':'adult:head-wound', '尸横遍野':'adult:corpses',
            '捅刀子':'adult:knife-attack', '杀人灭口':'adult:killing',
            '毒死你':'adult:poison', '脑浆迸裂':'adult:brain-explosion',
            '游戏里爆头':'adult:headshot', '剁手':'adult:hand-chop',
        }
        for text,intent in expected.items():
            with self.subTest(text=text):
                self.assertIn(intent,{hit['intent'] for hit in matcher.search(text)['matches']})
        for text in ('今天开车去公司','开房间的空调','比赛擦边球进了',
                     '我喜欢重口味火锅','万圣节暴打小朋友','手机爆头条新闻',
                     '特色图片','角色诱导','病毒杀灭','今天网购又要剁手了',
                     '形形色色'):
            with self.subTest(ordinary=text):
                self.assertEqual(matcher.search(text)['matches'],[])


class VariantBuildTests(unittest.TestCase):
    def test_every_generated_variant_is_a_valid_inventory_entry(self):
        rows=json.loads(Path('data/emoji_inventory.json').read_text())
        valid={r['emoji'] for r in rows}
        data=variant_data(rows)
        for entry in data.values():
            for family in entry.values():
                self.assertTrue(set(family.values()) <= valid)
        self.assertEqual(data[normalize('🧑‍💻')]['female']['3'],'👩🏽‍💻')

    def test_generated_modules_match_sources(self):
        rows=json.loads(Path('data/emoji_inventory.json').read_text())
        expected='-- Unicode-3.0; generated from pinned Emoji 16.0 inventory\nreturn '+lua_value(variant_data(rows))+'\n'
        self.assertEqual(Path('rime/lua/shi_emoji/variant_data.lua').read_text(),expected)
        adult=json.loads(Path('data/adult_phrases.json').read_text())
        self.assertEqual(Path('rime/lua/shi_emoji/adult.lua').read_text(),runtime_source(adult))


@unittest.skipUnless(lua_tests.LUA_LIBRARY,'Needs Lua')
class PreferenceLuaTests(unittest.TestCase):
    def test_expanded_edgy_candidates_and_false_positives(self):
        lua_tests.LuaFilterTests().execute("""
          local cases={
            {'今晚想看涩图','今晚想看涩图 🔞🖼️'},
            {'这个地狱笑话太冷了','这个地狱笑话太冷了 💀😂'},
            {'这场面血流成河','这场面血流成河 🩸'},
            {'今晚去开房','今晚去开房 🏨🔞'},
            {'头破血流','头破血流 🤕 🩸'},
            {'今天开车去公司',false},
            {'手机爆头条新闻',false},
            {'特色图片',false},
            {'形形色色',false},
            {'万圣节暴打小朋友',false},
          }
          for _,case in ipairs(cases) do
            output={};run({Candidate('sentence',0,6,case[1],'')})
            local edgy=output[1].comment:match('〔重口 (.-)〕')
            local expected=case[2] and case[2]:sub(#case[1]+2) or nil
            assert(edgy==expected,case[1]..': '..tostring(edgy))
          end
        """, settings={"adult": True})

    def test_basic_action_is_available_without_adult_extension(self):
        lua_tests.LuaFilterTests().execute("""
          run({Candidate('sentence',0,6,'万圣节暴打小朋友','')})
          assert(output[1].comment:find('🎃 👊 🧒',1,true),output[1].comment)
          assert(not package.loaded['shi_emoji.adult'])
        """)
        lua_tests.LuaFilterTests().execute("""
          run({Candidate('sentence',0,6,'万圣节暴打小朋友','')})
          assert(output[1].comment:find('🎃 👊 👧',1,true),output[1].comment)
          assert(not package.loaded['shi_emoji.adult'])
        """, settings={"gender": "female"})

    def test_main_switch_and_ascii_block_adult_lookup(self):
        lua_tests.LuaFilterTests().execute("""
          env.engine.context.get_option=function() return false end
          run({Candidate('sentence',0,6,'涩涩','')})
          assert(#output==1 and not package.loaded['shi_emoji.adult'])
          env.engine.context.get_option=function(_,n) return n=='shi_emoji' or n=='ascii_mode' end
          output={};run({Candidate('sentence',0,6,'涩涩','')})
          assert(#output==1 and not package.loaded['shi_emoji.adult'])
        """, settings={"adult": True})

    def test_gender_skin_explicit_words_and_unsupported_emoji(self):
        lua_tests.LuaFilterTests().execute("""
          local variants=require('shi_emoji.variants')
          local settings={gender='female',skin='medium'}
          assert(variants.apply('🧑‍💻','开发',settings)=='👩🏽‍💻')
          assert(variants.apply('👨‍🔬','男科学家',settings)=='👨🏽‍🔬')
          assert(variants.apply('👩‍🔬','女科学家',settings)=='👩🏽‍🔬')
          assert(variants.apply('🧒','小朋友',settings)=='👧🏽')
          assert(variants.apply('🐂🍺','牛逼',settings)=='🐂🍺')
          assert(variants.apply('🍆','茄子',settings)=='🍆')
        """)

    def test_static_adult_off_and_on_preserve_ordinary_candidates(self):
        lua_tests.LuaFilterTests().execute("""
          run({Candidate('sentence',0,6,'涩涩','')})
          assert(#output==1 and not package.loaded['shi_emoji.adult'])
        """)
        lua_tests.LuaFilterTests().execute("""
          run({Candidate('sentence',0,6,'涩涩','')})
          assert(#output==1 and output[1].comment:find('〔重口 🍆🍑',1,true))
          output={};run({Candidate('sentence',0,6,'开车','')})
          assert(#output==1 and output[1].text=='开车')
          assert(output[1].comment:find('〔诗Emoji 🚗',1,true))
          assert(output[1].comment:find('〔重口 🔞🚗',1,true))
        """, settings={"adult": True})
