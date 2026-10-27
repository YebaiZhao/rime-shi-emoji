import json
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ReleaseDocTests(unittest.TestCase):
    def test_release_version_matches_python_metadata(self):
        release=json.loads((ROOT/'release.json').read_text())
        version=re.search(r'^version = "([^"]+)"', (ROOT/'pyproject.toml').read_text(),re.M).group(1)
        self.assertEqual(release['python_version'],version)
        self.assertEqual(release['tag'],'v'+release['version'])
        self.assertIn(release['tag'],(ROOT/'README.md').read_text())

    def test_install_fenced_yaml_matches_shipped_examples(self):
        # Text equality avoids requiring PyYAML for portable documentation checks.
        blocks=re.findall(r'```yaml\n(.*?)```',(ROOT/'INSTALL.md').read_text(),re.S)
        self.assertEqual(len(blocks),2)
        for block,name in zip(blocks,['shi_emoji_phrase.custom.yaml.example','shi_emoji.default.custom.yaml.example']):
            source=(ROOT/'rime'/name).read_text()
            source='\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#')).strip()
            self.assertEqual(block.strip(),source)

    def test_local_markdown_links_resolve(self):
        for path in [*ROOT.glob('*.md'),*(ROOT/'docs').glob('*.md')]:
            for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
                target=target.split('#',1)[0]
                if not target or '://' in target or target.startswith('mailto:'):
                    continue
                self.assertTrue((path.parent/target).exists(),f'{path.name}: {target}')

    def test_license_notices_and_no_runtime_model_claims(self):
        notices=(ROOT/'THIRD_PARTY_NOTICES.md').read_text()
        self.assertIn('Unicode-3.0',notices)
        self.assertIn('jieba',notices)
        self.assertIn('not bundled',notices)
        self.assertIn('UNICODE LICENSE V3',(ROOT/'licenses/Unicode-3.0.txt').read_text())
        self.assertIn('Copyright (c) 2013 Sun Junyi',(ROOT/'licenses/jieba-MIT.txt').read_text())
