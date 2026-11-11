import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile
import test_lua_filter as lua_tests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_runtime", ROOT / "scripts/package_runtime.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackageTests(unittest.TestCase):
    def test_reproducible_allowlist_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "a.zip", Path(directory) / "b.zip"
            packager.package(ROOT, first)
            packager.package(ROOT, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                files = archive.namelist()
                self.assertEqual(len(files), 50)
                self.assertNotIn('rime-shi-emoji/lua/shi_emoji/data.lua', files)
                self.assertIn('rime-shi-emoji/lua/shi_emoji/match_metadata.lua', files)
                self.assertIn('rime-shi-emoji/lua/shi_emoji/word_boundary.lua', files)
                self.assertIn('rime-shi-emoji/lua/shi_emoji/boundary_data.lua', files)
                self.assertIn('rime-shi-emoji/lua/shi_emoji/entry_data.lua', files)
                self.assertIn('rime-shi-emoji/lua/shi_emoji/tier_data.lua', files)
                self.assertIn('rime-shi-emoji/docs/basic-keywords-116.md', files)
                self.assertTrue(any(n.endswith('/adult.lua') for n in files))
                self.assertIn('rime-shi-emoji/docs/experimental-candidate-slot.md', files)
                self.assertIn('rime-shi-emoji/docs/experimental-zero-key.md', files)
                self.assertIn('rime-shi-emoji/docs/reverse-audit.md', files)
                self.assertIn('rime-shi-emoji/docs/manual-integration.md', files)
                self.assertIn('rime-shi-emoji/licenses/OpenCC-Apache-2.0.txt', files)
                manifest = json.loads(archive.read("rime-shi-emoji/MANIFEST.sha256.json"))
                self.assertEqual(set(files), {"rime-shi-emoji/" + n for n in manifest} |
                                 {"rime-shi-emoji/MANIFEST.sha256.json"})
                for name, digest in manifest.items():
                    self.assertEqual(hashlib.sha256(archive.read("rime-shi-emoji/" + name)).hexdigest(), digest)
                for name in files:
                    self.assertFalse(Path(name).is_absolute())
                    self.assertNotIn("..", Path(name).parts)
                    self.assertNotIn("userdb", name)
                for name in ('README.md', 'README.en.md', 'INSTALL.md'):
                    content = archive.read('rime-shi-emoji/' + name).decode()
                    for target in re.findall(r'\]\(([^)]+)\)', content):
                        target = target.split('#', 1)[0]
                        if not target or '://' in target or target.startswith('mailto:'):
                            continue
                        resolved = (Path(name).parent / target).as_posix()
                        self.assertIn('rime-shi-emoji/' + resolved, files, f'{name}: {target}')

    @unittest.skipUnless(lua_tests.LUA_LIBRARY, "Needs Lua runtime")
    def test_extracted_archive_runs_without_checkout_lua(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "runtime.zip"
            packager.package(ROOT, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(Path(directory) / "extracted")
            lua_root = Path(directory) / "extracted/rime-shi-emoji/lua"
            lua_tests.LuaFilterTests().execute("""
              assert(not package.path:find('/rime/lua/',1,true))
              assert(filter.suffix('虾仁',CONFIG,2)=='🦐 🍤')
              assert(not package.loaded['shi_emoji.data'], 'Three tiers must not load the legacy mapping')
              run({Candidate('sentence',0,6,'电动车','')})
              assert(output[1].text=='电动车' and output[1].comment:find('🛵 🔋',1,true))
              assert(filter.suffix('害羞的笑脸',CONFIG,2)=='😊')
              assert(filter.suffix('红脸',CONFIG,2)=='😳')
              assert(filter.suffix('涩涩',CONFIG,3)=='🍆🍑', 'Single package includes extension')
              assert(filter.suffix('門衛幫忙收快遞',CONFIG,2):find('📦',1,true))
              assert(filter.suffix('来自在校学生的反馈',CONFIG,2)==nil)
              output={}
              require('shi_emoji.pinyin').func('kubiaozhi',
                {start=0,_end=9,has_tag=function(_,tag) return tag=='abc' end},
                {engine={context={input='kubiaozhi',get_option=function(_,key) return key=='shi_emoji' end}}})
              assert(#output==1 and output[1].text=='酷标志', 'Extracted optional name translator')
            """, lua_root=lua_root, settings={"adult": True})
