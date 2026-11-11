"""Batch native pinyin/preview/commit evidence in a disposable Wanxiang profile.

Pinyin is a generated search attempt, not a guarantee that the host dictionary
contains the exact reviewed Chinese name. Missing candidates remain explicit.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import re

from pypinyin import lazy_pinyin
from rime_probe import Api, Commit, Context, Traits, sized
from shi_emoji.reachability import contains

ROOT = Path(__file__).resolve().parents[1]
PINYIN_OVERRIDES = {'系丝带的心':'jisidaidexin', '长棍面包':'changgunmianbao',
                    '长鼻子鬼面':'changbiziguimian'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pages', type=int, default=5)
    parser.add_argument('--terms', nargs='+', help='Retry only these exact reviewed names')
    parser.add_argument('--input', type=Path, help='Reviewed queries: {entries: [{term, targets, pinyin}]}')
    parser.add_argument('--both-modes', action='store_true', help='Also replay and check 0 text-plus-emoji commit')
    parser.add_argument('--tier', choices=('strict', 'general'), default='general')
    args = parser.parse_args()
    if not (args.profile / '.shi-emoji-probe').is_file() or args.pages < 1:
        parser.error('Requires a marked disposable profile and positive page limit')
    framework = Path('/Library/Input Methods/Squirrel.app/Contents/Frameworks')
    lib = C.CDLL(str(framework/'librime.1.dylib'), mode=C.RTLD_GLOBAL)
    plugin = C.CDLL(str(framework/'rime-plugins/librime-lua.dylib'), mode=C.RTLD_GLOBAL)
    lib.rime_get_api.restype = C.POINTER(Api)
    api = lib.rime_get_api().contents

    def fn(name, result, *types):
        return C.CFUNCTYPE(result, *types)(getattr(api, name))

    traits = sized(Traits)
    traits.shared_data_dir = b'/Library/Input Methods/Squirrel.app/Contents/SharedSupport'
    traits.user_data_dir = str(args.profile.resolve()).encode()
    traits.app_name = b'rime.shi_entry_repairs_probe'
    traits.min_log_level = 2
    traits.modules = (C.c_char_p * 3)(b'default', b'lua', None)
    fn('setup', None, C.POINTER(Traits))(C.byref(traits))
    fn('initialize', None, C.POINTER(Traits))(C.byref(traits))
    session = fn('create_session', C.c_size_t)()
    simulate = fn('simulate_key_sequence', C.c_int, C.c_size_t, C.c_char_p)
    clear = fn('clear_composition', None, C.c_size_t)
    option = fn('set_option', None, C.c_size_t, C.c_char_p, C.c_int)

    def menu():
        context = sized(Context)
        fn('get_context', C.c_int, C.c_size_t, C.POINTER(Context))(session, C.byref(context))
        result = {'page_no': context.menu.page_no, 'last_page': bool(context.menu.is_last_page),
                  'highlighted': context.menu.highlighted_candidate_index,
                  'candidates': [{'text': context.menu.candidates[i].text.decode(),
                                  'comment': (context.menu.candidates[i].comment or b'').decode()}
                                 for i in range(context.menu.num_candidates)]}
        fn('free_context', C.c_int, C.POINTER(Context))(C.byref(context))
        return result

    def commit():
        value = sized(Commit)
        text = ''
        if fn('get_commit', C.c_int, C.c_size_t, C.POINTER(Commit))(session, C.byref(value)):
            text = value.text.decode()
            fn('free_commit', C.c_int, C.POINTER(Commit))(C.byref(value))
        return text

    input_path = args.input or ROOT/'data/entry_repairs_262.json'
    manifest = json.loads(input_path.read_text())
    rows = manifest['entries'] + manifest.get('preservation_entries', [])
    runtime = args.profile/'lua/shi_emoji'
    sources = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(runtime.glob('*.lua'))}
    if args.terms:
        assert set(args.terms) <= {row['term'] for row in rows}, 'Unknown reviewed name'
        rows = [row for row in rows if row['term'] in args.terms]
    results = []
    try:
        assert fn('select_schema', C.c_int, C.c_size_t, C.c_char_p)(session, b'wanxiang')
        for name, value in {'ascii_mode':False, 'shi_emoji':True, 'shi_emoji_general':args.tier == 'general',
                            'shi_emoji_strict':args.tier == 'strict', 'shi_emoji_divergent':False,
                            'shi_emoji_emoji_only':False}.items():
            option(session, name.encode(), value)
        for index, row in enumerate(rows, 1):
            clear(session)
            commit()
            keys = row.get('pinyin') or PINYIN_OVERRIDES.get(row['term'], ''.join(lazy_pinyin(row['term'])).lower())
            result = {'term': row['term'], 'targets': row['targets'], 'keys': keys,
                      'pinyin_candidate': {'status':'not_found_within_limit'},
                      'comment':'', 'suffix':'', 'commit':'', 'pages_observed':[]}
            simulate(session, keys.encode())
            selected_keys = keys
            for _ in range(args.pages):
                observed = menu()
                result['pages_observed'].append(observed)
                found = next((i for i, c in enumerate(observed['candidates']) if c['text']==row['term']), None)
                if found is not None:
                    delta = found - observed['highlighted']
                    movement = ('{Down}' if delta >= 0 else '{Up}') * abs(delta)
                    selected_keys += movement
                    simulate(session, movement.encode())
                    selected = menu()
                    candidate = selected['candidates'][selected['highlighted']]
                    assert candidate['text'] == row['term'], (row, selected)
                    suffix = re.search(r'〔0→(.*?)〕', candidate['comment'])
                    simulate(session, b'{Alt+0}')
                    result.update(pinyin_candidate={'status':'found', 'page':observed['page_no']+1,
                                                    'position':found+1}, comment=candidate['comment'],
                                  suffix=suffix.group(1) if suffix else '', commit=commit(), selected_keys=selected_keys)
                    if args.both_modes:
                        clear(session)
                        simulate(session, selected_keys.encode())
                        repeated = menu()
                        assert repeated['candidates'][repeated['highlighted']]['text'] == row['term']
                        simulate(session, b'0')
                        result['text_commit'] = commit()
                        result['text_commit_passed'] = result['text_commit'] == row['term']+' '+result['suffix']
                    break
                if observed['last_page']:
                    break
                simulate(session, b'{Page_Down}')
                selected_keys += '{Page_Down}'
            result['preview_passed'] = all(contains(result['suffix'], t) for t in row['targets'])
            result['commit_passed'] = all(contains(result['commit'], t) for t in row['targets'])
            results.append(result)
            if index % 25 == 0:
                print(f'{index} names checked', flush=True)
    finally:
        fn('destroy_session', C.c_int, C.c_size_t)(session)
        fn('finalize', None)()
    result = {'scope':f'Headless native librime + Squirrel Lua; disposable Wanxiang, {args.tier}, neutral gender, default skin, adult=false. Alt+0 emoji-only. No GUI/application insertion claim.',
              'page_limit':args.pages, 'pinyin_method':'pypinyin.lazy_pinyin; lowercase full pinyin with explicit polyphonic corrections',
              'pinyin_overrides':PINYIN_OVERRIDES,
              'runtime_sha256':sources, 'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
              'both_modes':args.both_modes,
              'schema_sha256':hashlib.sha256((args.profile/'build/wanxiang.schema.yaml').read_bytes()).hexdigest(),
              'compiled_assets_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted((args.profile/'build').glob('wanxiang*.bin'))},
              'summary':{'terms':len(results),
                         'found':sum(r['pinyin_candidate']['status']=='found' for r in results),
                         'preview_passed':sum(r['preview_passed'] for r in results),
                         'commit_passed':sum(r['commit_passed'] for r in results),
                         'text_commit_passed':sum(r.get('text_commit_passed',False) for r in results)},
              'entries':results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
