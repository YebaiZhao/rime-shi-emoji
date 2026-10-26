"""Archive-backed lifecycle in a disposable profile, never the active user DB."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("RIME_PROBE_USER"), "Needs isolated compiled Rime assets")
class RuntimeInstallationTests(unittest.TestCase):
    def test_archive_install_disable_and_uninstall_preserve_original_candidates(self):
        import yaml
        import test_package
        with tempfile.TemporaryDirectory(dir=ROOT / "dist", prefix="release-probe-") as directory:
            temp = Path(directory)
            package = temp / "runtime.zip"
            test_package.packager.package(ROOT, package)
            with zipfile.ZipFile(package) as archive:
                archive.extractall(temp / "extracted")
            runtime = temp / "extracted/rime-shi-emoji/lua/shi_emoji"
            profile = temp / "profile"
            subprocess.run([sys.executable, "scripts/prepare_wanxiang_probe.py", "--source",
                            os.environ["RIME_PROBE_USER"], "--output", str(profile),
                            "--runtime", str(runtime)], cwd=ROOT, check=True, capture_output=True, text=True)

            def probe(state):
                result = subprocess.run([sys.executable, "scripts/rime_probe.py", "--user", str(profile),
                                         "--keys", "diandongche", "--option-state", state], cwd=ROOT,
                                        check=True, capture_output=True, text=True)
                return json.loads(result.stdout)["candidates"]

            disabled = probe("off")
            enabled = probe("on")
            self.assertEqual([r['text'] for r in enabled], [r['text'] for r in disabled])
            self.assertIn("🛵 🔋", enabled[0]["comment"])
            self.assertEqual(probe("off"), disabled)

            # Remove only this plugin from this disposable profile, retaining
            # the original schema components and static dictionaries.
            schema_path = profile / "build/wanxiang.schema.yaml"
            schema = yaml.safe_load(schema_path.read_text())
            for key in ("processors", "filters"):
                schema["engine"][key] = [v for v in schema["engine"][key] if '@*shi_emoji.' not in v]
            schema["switches"] = [v for v in schema["switches"] if not v.get("name",'').startswith('shi_emoji')
                                  and not any(o.startswith('shi_emoji') for o in v.get('options',[]))]
            schema_path.write_text(yaml.safe_dump(schema, allow_unicode=True))
            default_path = profile / "build/default.yaml"
            default = yaml.safe_load(default_path.read_text())
            default["switcher"]["save_options"] = [v for v in default["switcher"]["save_options"] if not v.startswith('shi_emoji')]
            default_path.write_text(yaml.safe_dump(default, allow_unicode=True))
            (profile / "lua/shi_emoji").unlink()
            self.assertEqual(probe("off"), disabled)

    def test_native_preference_menus_persist_and_bundled_extension(self):
        import test_package
        with tempfile.TemporaryDirectory(dir=ROOT/'dist',prefix='preferences-probe-') as directory:
            temp=Path(directory)
            archive_path=temp/'runtime.zip'
            test_package.packager.package(ROOT,archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temp/'extracted')
            runtime=temp/'extracted/rime-shi-emoji/lua/shi_emoji'
            profile=temp/'profile'
            subprocess.run([sys.executable,'scripts/prepare_wanxiang_probe.py','--source',os.environ['RIME_PROBE_USER'],
                            '--output',str(profile),'--runtime',str(runtime)],check=True,capture_output=True,text=True)
            def probe(keys, labels=()):
                command=[sys.executable,'scripts/rime_probe.py','--user',str(profile),'--option-state','on','--keys',keys]
                for label in labels: command+=['--menu-select',label]
                return json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)
            result=probe('kaifa{Alt+Return}',['女性表情','中肤色','重口联想关'])
            self.assertEqual(result['commit'],'开发 👩🏽‍💻')
            self.assertEqual(probe('kaifa{Alt+Return}')['commit'],'开发 👩🏽‍💻')
            rows=probe('sese')['candidates']
            self.assertFalse(any('〔重口 ' in r['comment'] for r in rows),rows)
            rows=probe('sese{Down}')['candidates']
            self.assertTrue(any(r['text'] in {'涩涩','色色'} and '〔重口 🍆🍑' in r['comment'] for r in rows),rows)
            rows=probe('sese',['重口联想开'])['candidates']
            self.assertFalse(any('〔重口 ' in r['comment'] for r in rows))
            self.assertFalse(any('〔重口 ' in r['comment'] for r in probe('sese')['candidates']))
