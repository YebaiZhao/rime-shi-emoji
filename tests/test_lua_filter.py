"""Exercise fallback interpretation and partial-segment boundaries in actual Lua."""
import ctypes as C
import ctypes.util
import json
from pathlib import Path
import unittest

BASE = Path("/Library/Input Methods/Squirrel.app/Contents/Frameworks")
RIME_LUA = BASE / "rime-plugins/librime-lua.dylib"
LUA_LIBRARY = str(RIME_LUA) if RIME_LUA.exists() else C.util.find_library("lua5.4")


@unittest.skipUnless(LUA_LIBRARY, "Needs Squirrel Lua or system liblua5.4")
class LuaFilterTests(unittest.TestCase):
    def test_tier_matching_and_scope(self):
        self.execute("""
          local preferences={skin='default',gender='neutral'}
          assert(filter.suffix('冰',preferences,false,1)=='🧊')
          assert(filter.suffix('海狮',preferences,false,1)==nil)
          assert(filter.suffix('海狮',preferences,false,2)=='🦭')
          assert(filter.suffix('凤凰传奇',preferences,false,2)==nil)
          assert(filter.suffix('凤凰传奇',preferences,false,3)=='🐦‍🔥')
          local nested=filter.suffix('我刚看了凤凰传奇',preferences,false,3) or ''
          assert(not nested:find('🐦‍🔥',1,true))
          local invoice=filter.suffix('开发票',preferences,false,3) or ''
          assert(not invoice:find('🧑‍💻',1,true))
          local matcher=require('shi_emoji.matcher')
          local index=matcher.tiered({boundaries={},negators={}}, {
            ['甲']={{'A',1,true,false}}, ['甲乙']={{'B',3,true,false}},
            ['丙']={{'C',3,true,false}}, ['丁']={{'D',3,true,false}},
            ['戊']={{'E',2,false,false}},
          })
          local compose=require('shi_emoji.compose')
          local _,groups=matcher.search(index,'甲乙丙丁戊',100,3)
          assert(compose.suffix(groups)=='A C')
        """)

    def test_option_zero_output_modes_and_passthrough(self):
        self.execute("""
          local processor=require('shi_emoji.processor')
          env.zero_key=true
          env.settings=require('shi_emoji.settings').load(env.engine.schema.config)
          local options={shi_emoji=true, ascii_mode=false, shi_emoji_emoji_only=false}
          context.get_option=function(_, name) return options[name] or false end
          local committed,cleared
          env.engine.commit_text=function(_, text) committed=text end
          context.clear=function() cleared=true end
          local function key(code, modifiers)
            modifiers=modifiers or {}
            return {keycode=code,
              release=function() return modifiers.release or false end,
              alt=function() return modifiers.alt or false end,
              shift=function() return modifiers.shift or false end,
              ctrl=function() return modifiers.ctrl or false end,
              super=function() return modifiers.super or false end}
          end
          local function check(event, expected)
            committed=nil;cleared=false
            local result=processor.func(event,env)
            assert(result==(expected and 1 or 2), ('key=%x result=%s expected=%s'):format(event.keycode,result,tostring(expected)))
            assert(committed==expected, ('actual=%s expected=%s'):format(tostring(committed),tostring(expected)))
            assert(cleared==(expected~=nil))
          end
          run({Candidate('sentence',0,6,'虾仁','')})
          for _,only in ipairs({false,true}) do
            options.shi_emoji_emoji_only=only
            check(key(0x30), only and '🦐 🍤' or '虾仁 🦐 🍤')
            check(key(0x30,{alt=true}), only and '虾仁 🦐 🍤' or '🦐 🍤')
            check(key(0xff0d,{alt=true}), only and '虾仁 🦐 🍤' or '🦐 🍤')
          end
          check(key(0x30,{shift=true}),nil)
          check(key(0x29,{shift=true}),nil)
          check(key(0x30,{alt=true,release=true}),nil)
          for _,modifier in ipairs({'shift','ctrl','super'}) do
            check(key(0x30,{alt=true,[modifier]=true}),nil)
          end
          for _,name in ipairs({'shi_emoji','ascii_mode'}) do
            local saved=options[name];options[name]=not saved
            check(key(0x30,{alt=true}),nil);options[name]=saved
          end
          env.zero_key=false;check(key(0x30,{alt=true}),nil);env.zero_key=true
          output={}
          run({Candidate('sentence',0,6,'丙丁','')})
          check(key(0x30,{alt=true}),nil)
        """)

    def test_traditional_preview_and_explicit_gender(self):
        self.execute("""
          local a=Candidate('sentence',0,6,'開發','')
          run({a})
          assert(a.comment:find('👨‍💻',1,true),a.comment)
          output={};local b=Candidate('sentence',0,6,'開發票','')
          run({b})
          assert(b.comment=='',b.comment)
          output={};local c=Candidate('sentence',0,6,'女科學家','')
          run({c})
          assert(c.comment:find('👩‍🔬',1,true),c.comment)
        """, settings={"gender": "male"})

    def test_literal_cow_and_scoped_expression_outputs(self):
        for text, suffix in [('牛','🐄 🐂'),('老牛','🐄 🐂'),('黄牛','🐂 🐄'),
                             ('奶牛','🐄 🐮'),('牛逼','🐂🍺'),('虾仁','🦐 🍤'),
                             ('虾','🦐'),('苹果','🍎 🍏'),('蛋糕','🍰 🎂'),
                             ('乌龟','🐢'),('橙子','🍊'),('月亮','🌙 🌕')]:
            with self.subTest(text=text):
                self.execute("run({Candidate('sentence',0,6," + json.dumps(text, ensure_ascii=False)
                             + ",'')}); assert(#output==1 and output[1].text=="
                             + json.dumps(text,ensure_ascii=False) + "); assert(output[1].comment:find("
                             + json.dumps(suffix,ensure_ascii=False) + ",1,true), output[1].comment)")
    def test_word_guard_corpus_matches_python_in_actual_lua(self):
        from shi_emoji.match import Matcher
        matcher = Matcher.load('data/phrases.json')
        body = ["local matcher=require('shi_emoji.matcher'); local index=matcher.new(require('shi_emoji.data'))"]
        for case in json.loads(Path('data/matching_cases.json').read_text()):
            text = json.dumps(case['text'], ensure_ascii=False)
            expected = sorted(r['emoji'] for r in matcher.search(case['text'], 100)['candidates'])
            body.append('do local rows=matcher.search(index,' + text + ',100); local found={}; for _,r in ipairs(rows) do found[r.emoji]=true end')
            body.append('assert(#rows==' + str(len(expected)) + ', ' + text + ')')
            for emoji in expected:
                body.append('assert(found[' + json.dumps(emoji, ensure_ascii=False) + '], ' + text + ')')
            body.append('end')
        self.execute('\n'.join(body))

    def execute(self, body, lua_root=Path("rime/lua"), slot=False, settings=None):
        if RIME_LUA.exists():
            self.rime = C.CDLL(str(BASE / "librime.1.dylib"), mode=C.RTLD_GLOBAL)
        lua = C.CDLL(LUA_LIBRARY, mode=C.RTLD_GLOBAL)
        lua.luaL_newstate.restype = C.c_void_p
        lua.luaL_openlibs.argtypes = [C.c_void_p]
        lua.luaL_loadstring.argtypes = [C.c_void_p, C.c_char_p]
        lua.lua_pcallk.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_longlong, C.c_void_p]
        lua.lua_tolstring.argtypes = [C.c_void_p, C.c_int, C.c_void_p]
        lua.lua_tolstring.restype = C.c_char_p
        lua.lua_close.argtypes = [C.c_void_p]
        state = lua.luaL_newstate()
        lua.luaL_openlibs(state)
        prefix = str((lua_root / "?.lua").resolve()) + ";"
        settings = {"skin": "default", "gender": "neutral", "adult": False} | (settings or {})
        configuration = "local CONFIG={skin=" + json.dumps(settings["skin"]) + ",gender=" + json.dumps(settings["gender"]) + ",adult=" + json.dumps(settings["adult"]) + "}\n"
        script = "package.path = " + json.dumps(prefix, ensure_ascii=False) + " .. package.path\n" + configuration + """
          local output = {}
          function yield(candidate) output[#output + 1] = candidate end
          function Candidate(kind, start, finish, text, comment)
            return {type=kind, start=start, _end=finish, text=text, comment=comment}
          end
          function ShadowCandidate(original, kind, text, comment)
            return {type=kind, start=original.start, _end=original._end,
              text=text, comment=comment, original=original}
          end
          local filter = require('shi_emoji.filter')
          local context
          context = {input='abcdef', selected_index=1,
            get_option=function(_, name) return name=='shi_emoji' end,
            composition={back=function() return {prompt='', selected_index=context.selected_index-1,
              menu={get_candidate_at=function(_, index) return output[index+1] end}} end},
            update_notifier={connect=function(_, callback)
              on_update=callback
              return {disconnect=function() end}
            end},
            get_selected_candidate=function(self) return output[self.selected_index] end}
          local env = {engine={context=context, schema={config={
            get_bool=function(_, key)
              if key=='shi_emoji/adult' then return CONFIG.adult end
              return key=='shi_emoji/candidate_slot' and SLOT_ENABLED
            end,
            get_string=function(_, key)
              if key=='shi_emoji/skin' then return CONFIG.skin end
              if key=='shi_emoji/gender' then return CONFIG.gender end
            end,
            get_int=function(_, key) return key=='menu/page_size' and 7 end
          }}}}
          filter.init(env)
          local function run(rows)
            context.selected_index=1
            local translation = {iter=function()
              local i=0
              return function() i=i+1; return rows[i] end
            end}
            filter.func(translation, env)
            on_update(context)
          end
          local function select(index)
            context.selected_index=index
            on_update(context)
          end
        """.replace("SLOT_ENABLED", "true" if slot else "false") + body
        try:
            status = lua.luaL_loadstring(state, script.encode())
            if status == 0:
                status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
            self.assertEqual(status, 0, (lua.lua_tolstring(state, -1, None) or b"").decode())
        finally:
            lua.lua_close(state)

    def test_each_full_interpretation_has_its_own_preview(self):
        self.execute("""
          local a=Candidate('sentence',0,6,'吓人','释义')
          local b=Candidate('sentence',0,6,'虾仁','')
          local c=Candidate('sentence',0,6,'丙丁','')
          run({a,b,c})
          assert(#output==3 and output[1].text=='吓人' and output[2].text=='虾仁')
          assert(output[1].comment:find('释义',1,true)==1)
          assert(output[1].comment=='释义')
          assert(output[2].comment=='')
          select(2)
          assert(output[1].comment=='释义')
          assert(output[2].comment:find('🦐 🍤',1,true))
          select(3)
          assert(output[2].comment=='' and output[3].comment=='')
        """)

    def test_short_candidate_preview_is_quiet_until_context_is_longer(self):
        self.execute("""
          for _,word in ipairs({'病','好','好人','你'}) do
            output={};run({Candidate('sentence',0,6,word,'')})
            assert(output[1].comment=='',word)
          end
          output={};run({Candidate('sentence',0,6,'冰','')})
          assert(output[1].comment:find('🧊',1,true))
          output={};run({Candidate('sentence',0,6,'你真是一个好人','')})
          assert(output[1].comment:find('🫵 🦸',1,true),output[1].comment)
        """)

    def test_dynamic_candidate_slot_follows_short_and_full_pages(self):
        self.execute("""
          run({Candidate('sentence',0,6,'吓人',''),Candidate('sentence',0,6,'虾仁','')})
          assert(#output==3 and output[3].type=='shi_emoji')
          assert(output[3].text=='吓人',output[3].text)
          select(2)
          assert(output[3].text=='🦐 🍤',output[3].text)
          local rows={}
          for i=1,5 do rows[i]=Candidate('sentence',0,6,'甲乙','') end
          rows[6]=Candidate('sentence',0,6,'虾仁','')
          rows[7]=Candidate('sentence',0,6,'海边','')
          output={};run(rows)
          assert(#output==9 and output[7].type=='shi_emoji' and output[8]==rows[7])
          select(6)
          assert(output[7].text=='🦐 🍤',output[7].text)
          select(8)
          assert(output[9].type=='shi_emoji' and output[9].text=='🏖️')
        """, slot=True)

    def test_partial_word_is_not_used_for_whole_sentence_enhancement(self):
        self.execute("""
          local a=Candidate('sentence',0,6,'甲乙','')
          local b=Candidate('phrase',0,2,'海边','')
          run({a,b})
          assert(#output==2 and output[1]==a and output[2]==b)
        """)

    def test_multiple_concepts_and_nested_child_phrase(self):
        self.execute("""
          run({Candidate('sentence',0,6,'万圣节暴走小朋友','')})
          assert(#output==1 and output[1].comment:find('🎃 🏃 🧒',1,true))
        """)

    def test_combo_preserved_alongside_other_concepts(self):
        self.execute("""
          run({Candidate('sentence',0,6,'牛逼海边','')})
          assert(#output==1 and output[1].comment:find('🐂🍺 🏖️',1,true))
        """)

    def test_curated_meaning_and_country_priority(self):
        self.execute("""
          local cases={
            {'厉害','厉害 👏 👍'}, {'牛马','牛马 🐂🐎'},
            {'中国','中国 🇨🇳 🐉'}, {'见一面','见一面 🤝'},
            {'房地产开发',false}, {'开发房地产',false}, {'发展中国家',false},
          }
          for _,case in ipairs(cases) do
            output={};run({Candidate('sentence',0,6,case[1],'')})
            if case[2] then
              assert(#output==1 and output[1].text==case[1])
              assert(output[1].comment:find(case[2]:sub(#case[1]+2),1,true),case[1])
            else
              assert(#output==1 and output[1].comment=='',case[1])
            end
          end
        """)

    def test_lexical_baseline_is_visible_in_real_lua_filter(self):
        for text, suffix in [('德国', '🇩🇪'), ('三文鱼', '🍣'), ('飞人', '🕴️'),
                             ('女科学家', '👩‍🔬'), ('禁止使用手机', '📵')]:
            with self.subTest(text=text):
                self.execute("run({Candidate('sentence',0,6," + json.dumps(text, ensure_ascii=False)
                             + ",'')}); assert(output[1].comment:find("
                             + json.dumps(suffix, ensure_ascii=False) + ",1,true), output[1].comment)")
