"""Check every reviewed relation against the actual runtime matcher."""
import json
from pathlib import Path
import unittest

from shi_emoji.export import lua_value
from shi_emoji.tier_export import LEVEL
import test_lua_filter as lua_tests


@unittest.skipUnless(lua_tests.LUA_LIBRARY, "Actual Lua required")
class SentenceScopeRuntimeTests(unittest.TestCase):
    def test_all_reviewed_relations_obey_their_scope(self):
        directory = Path("data")
        ledger = {row["id"]: row for line in (directory / "relation_reviews.jsonl").read_text().splitlines()
                  for row in [json.loads(line)]}
        cases = []
        for batch in sorted((directory / "sentence_scope_review").glob("batch-[0-9][0-9][0-9].jsonl")):
            for line in batch.read_text().splitlines():
                row = json.loads(line)
                cases.append([row["expression"], row["target"].replace("\ufe0f", ""),
                              LEVEL[row["min_tier"]], row["decision"] == "whole_token",
                              ledger[row["id"]]["content_gate"]])
        self.assertEqual(len(cases), 5388)
        self.assertEqual(sum(row[3] for row in cases), 2590)
        lua_tests.LuaFilterTests().execute("local cases=" + lua_value(cases) + """
          local matcher=require('shi_emoji.matcher')
          local metadata=require('shi_emoji.match_metadata')
          local normal=matcher.tiered(metadata,require('shi_emoji.tier_data'))
          local indexes={normal=normal,adult=matcher.tiered_extension(normal,require('shi_emoji.adult'))}
          local function has(index,text,expression,target,tier)
            local _,groups=matcher.search(index,text,100,tier)
            for _,group in ipairs(groups) do
              if group.phrase==expression then
                for _,emoji in ipairs(group.emoji) do
                  if emoji:gsub('️','')==target then return true end
                end
              end
            end
            return false
          end
          for _,case in ipairs(cases) do
            local expression,target,tier,embedded,gate=table.unpack(case)
            local index=indexes[gate]
            local sentence='稍候，'..expression..'。'
            local message=expression..' → '..target
            assert(has(index,expression,expression,target,tier), 'exact: '..message)
            assert(not has(index,expression,expression,target,tier-1), 'tier: '..message)
            assert(has(index,sentence,expression,target,tier)==embedded, 'sentence: '..message)
          end
        """)
