"""Observe reviewed pinyin entries in a marked disposable Wanxiang profile."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pages', type=int, default=5)
    args = parser.parse_args()
    if not (args.profile / '.shi-emoji-probe').is_file():
        parser.error('Use a disposable profile made by prepare_wanxiang_probe.py')
    if args.pages < 1:
        parser.error('--pages must be positive')

    def probe(keys):
        proc = subprocess.run([sys.executable, str(ROOT/'scripts/rime_probe.py'), '--user',
                               str(args.profile), '--keys', keys, '--option-state', 'on',
                               '--menu-select', '诗Emoji严格'], check=True, capture_output=True, text=True)
        return json.loads(proc.stdout)

    rows = json.loads((ROOT/'data/common_entry_reviews.json').read_text())['entries']
    results = []
    for row in rows:
        scanned = []
        result = {'term': row['term'], 'targets': row['targets'], 'keys': row['pinyin']}
        for page in range(args.pages):
            keys = row['pinyin'] + '{Page_Down}' * page
            menu = probe(keys)
            scanned.append({'page_no': menu['page_no'], 'candidates': [r['text'] for r in menu['candidates']]})
            index = next((i for i,r in enumerate(menu['candidates']) if r['text']==row['term']), None)
            if index is not None:
                # A page-down can preserve the highlighted position. Select
                # relative to the observed position, not an assumed first row.
                delta = index - menu['highlighted']
                selected = keys + ('{Down}' if delta >= 0 else '{Up}') * abs(delta)
                preview = probe(selected)
                candidate = preview['candidates'][preview['highlighted']]
                assert candidate['text'] == row['term'], preview
                comment = candidate['comment']
                suffix = re.search(r'〔0→(.*?)〕', comment)
                result.update(pinyin_candidate={'status':'found', 'page':menu['page_no']+1,
                                                'position':index+1, 'keys':row['pinyin']},
                              selected_keys=selected, comment=comment,
                              suffix=suffix.group(1) if suffix else '',
                              commit=probe(selected+'{Alt+0}')['commit'])
                break
        else:
            result.update(pinyin_candidate={'status':'not_found_within_limit', 'pages':args.pages,
                                            'keys':row['pinyin']}, comment='', suffix='', commit='')
        result['pages_observed'] = scanned
        results.append(result)
        print(row['term'], result['pinyin_candidate']['status'], result['commit'], flush=True)
    schema = args.profile/'build/wanxiang.schema.yaml'
    result = {'scope': 'Headless native librime + Squirrel Lua; isolated Wanxiang, strict tier, neutral gender, default skin, adult=false, Alt+0 emoji-only. This is C-API preview/commit, not a GUI/app insertion test.',
              'page_limit': args.pages,
              'runtime_sha256': hashlib.sha256((ROOT/'rime/lua/shi_emoji/tier_data.lua').read_bytes()).hexdigest(),
              'reviews_sha256': hashlib.sha256((ROOT/'data/common_entry_reviews.json').read_bytes()).hexdigest(),
              'schema_sha256': hashlib.sha256(schema.read_bytes()).hexdigest(),
              'compiled_assets_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted((args.profile/'build').iterdir())
                                         if p.suffix == '.bin' and p.name.startswith('wanxiang')},
              'entries': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
