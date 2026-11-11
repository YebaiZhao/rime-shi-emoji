"""Full fixed-inventory entry audit against actual three-tier Lua suffixes.

CLDR names/keywords are discovery candidates, NOT approvals of natural usage.
Native observations are optional, and never inferred from Lua results.
"""
import argparse
from collections import defaultdict
import ctypes as C
import ctypes.util
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import tempfile

from .coverage import normalize
from .datafiles import merged_data
from .export import lua_value
from .tier_export import compile_rules, compile_entry_rules, entry_runtime_source

ROOT = Path(__file__).resolve().parents[2]
TIERS = ('strict', 'general', 'divergent')


def run_lua(script):
    """Execute a validation script in the actual Lua runtime."""
    base = Path('/Library/Input Methods/Squirrel.app/Contents/Frameworks')
    plugin = base / 'rime-plugins/librime-lua.dylib'
    library = str(plugin) if plugin.exists() else C.util.find_library('lua5.4')
    if not library:
        raise RuntimeError('Actual Lua required: install liblua5.4 or Squirrel')
    if plugin.exists():
        C.CDLL(str(base / 'librime.1.dylib'), mode=C.RTLD_GLOBAL)
    lua = C.CDLL(library, mode=C.RTLD_GLOBAL)
    lua.luaL_newstate.restype = C.c_void_p
    lua.luaL_openlibs.argtypes = [C.c_void_p]
    lua.luaL_loadstring.argtypes = [C.c_void_p, C.c_char_p]
    lua.lua_pcallk.argtypes = [C.c_void_p, C.c_int, C.c_int, C.c_int, C.c_longlong, C.c_void_p]
    lua.lua_tolstring.argtypes = [C.c_void_p, C.c_int, C.c_void_p]
    lua.lua_tolstring.restype = C.c_char_p
    lua.lua_close.argtypes = [C.c_void_p]
    state = lua.luaL_newstate()
    lua.luaL_openlibs(state)
    try:
        status = lua.luaL_loadstring(state, script.encode())
        if status == 0:
            status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise RuntimeError(lua.lua_tolstring(state, -1, None).decode())
    finally:
        lua.lua_close(state)


def lua_suffixes(terms, runtime, settings=None):
    """Execute the shipped composer/filter in Lua, once per term and tier."""
    with tempfile.TemporaryDirectory(prefix='shi-entry-lua-') as directory:
        output = Path(directory) / 'suffixes.tsv'
        script = '\n'.join([
            'package.path=' + lua_value(str(runtime.resolve() / '?.lua') + ';') + '..package.path',
            "local filter=require('shi_emoji.filter')",
            'local out=assert(io.open(' + lua_value(str(output)) + ',"w"))',
            'for _,term in ipairs(' + lua_value(terms) + ') do',
            ' for tier=1,3 do',
            "  out:write(filter.suffix(term," + lua_value(settings or {'skin': 'default', 'gender': 'neutral'}) + ",tier) or '', '\\n')",
            ' end', 'end', 'out:close()',
        ])
        run_lua(script)
        lines = output.read_text().splitlines()
    assert len(lines) == len(terms) * 3
    return {term: dict(zip(TIERS, lines[i*3:i*3+3])) for i, term in enumerate(terms)}


def contains(suffix, target):
    # Compare whole space-delimited output tokens; a component of a ZWJ emoji
    # or a fixed sequence must NOT count as an independently emitted target.
    return normalize(target) in [normalize(token) for token in suffix.split()]


def analyze(root=ROOT, native=None, baseline=False, natural_names=False):
    inventory = json.loads((root / 'data/emoji_inventory.json').read_text())
    base = [r for r in inventory if not r['skin_variant']]
    assert len(base) == 1906
    legacy = merged_data(root / 'data/phrases.json', include_traditional=False)
    tiered = compile_rules(root / 'data', include_common=not baseline)
    exact = {} if baseline else compile_entry_rules(root / 'data')
    reviews = json.loads((root / 'data/common_entry_reviews.json').read_text())['entries']
    if native:
        for field, path in [('runtime_sha256', 'rime/lua/shi_emoji/tier_data.lua'),
                            ('reviews_sha256', 'data/common_entry_reviews.json')]:
            assert native[field] == hashlib.sha256((root/path).read_bytes()).hexdigest(), 'Stale native evidence: '+field
    candidates = defaultdict(lambda: defaultdict(set))
    lexical = defaultdict(set)
    runtime = defaultdict(set)
    whole_candidate = defaultdict(set)
    reviewed = {}
    for row in base:
        target = normalize(row['emoji'])
        for name in row['names']:
            candidates[target][name].add('inventory_name')
        for name in row['keywords']:
            candidates[target][name].add('inventory_keyword')
    for rule in legacy['rules']:
        for target in rule['emoji']:
            for term in rule['phrases']:
                candidates[normalize(target)][term].add('legacy_mapping')
                lexical[term].add(normalize(target))
    for term, entries in compile_rules(root / 'data').items():
        for target, *_ in entries:
            candidates[normalize(target)][term].add('tier_candidate')
    for term, entries in tiered.items():
        for target, *_ in entries:
            runtime[term].add(normalize(target))
    for term, rule in exact.items():
        for target, _ in rule['targets']:
            whole_candidate[term].add(normalize(target))
            candidates[normalize(target)][term].add('whole_candidate_mapping')
    for row in reviews:
        for target in row['targets']:
            candidates[normalize(target)][row['term']].add('common_entry_review')
            reviewed[(normalize(target), row['term'])] = row
    name_rows = {}
    if natural_names:
        from .natural_names import build_reviews
        name_rows = {normalize(r['emoji']): r for r in build_reviews(root)}
        for target, row in name_rows.items():
            for name in row['names']:
                candidates[target][name['term']].add('individual_natural_name_review')
                reviewed[(target, name['term'])] = name
        from .pinyin_entries import validate_reviews
        for row in validate_reviews(root):
            term = row['selected_term']
            for emoji in row['targets']:
                target = normalize(emoji)
                candidates[target][term].add('pinyin_entry_review')
                reviewed[(target, term)] = {'rationale':row['rationale'], 'runtime_action':'pinyin_entry_review'}
        strict_names = json.loads((root / 'data/strict_entry_reviews.json').read_text())['entries']
        for row in strict_names:
            target, term = normalize(row['target']), row['term']
            candidates[target][term].add('strict_entry_review')
            reviewed[(target, term)] = {'rationale': row['rationale'], 'runtime_action': 'strict_entry_review'}
    terms = sorted({t for r in base for t in candidates[normalize(r['emoji'])]})
    from .tier_export import runtime_source
    compiled = runtime_source(tiered)
    if baseline:
        with tempfile.TemporaryDirectory(prefix='shi-entry-baseline-') as directory:
            lua_root = Path(directory)/'lua'
            shutil.copytree(root/'rime/lua', lua_root)
            (lua_root/'shi_emoji/tier_data.lua').write_text(compiled)
            (lua_root/'shi_emoji/entry_data.lua').write_text(entry_runtime_source({}))
            suffixes = lua_suffixes(terms, lua_root)
    else:
        assert (root/'rime/lua/shi_emoji/tier_data.lua').read_text() == compiled, 'Regenerate tier_data.lua first'
        assert (root/'rime/lua/shi_emoji/entry_data.lua').read_text() == entry_runtime_source(exact), 'Regenerate entry_data.lua first'
        suffixes = lua_suffixes(terms, root / 'rime/lua')
    observations = {r['term']: r for r in (native or {}).get('entries', [])}
    entries = []
    for number, row in enumerate(base, 1):
        target = normalize(row['emoji'])
        probes = []
        for term, sources in sorted(candidates[target].items()):
            review = reviewed.get((target, term))
            actual = suffixes[term]
            observation = observations.get(term)
            probes.append({
                'term': term, 'sources': sorted(sources),
                'natural_name': {'status': 'reviewed' if review else 'unverified',
                                 'rationale': review['rationale'] if review else None,
                                 **({'usage': review['usage']} if review and 'usage' in review else {}),
                                 'runtime_action': review['runtime_action'] if review else None},
                'lexicon': {'legacy_mapping': target in lexical[term],
                            'tier_mapping': target in runtime[term] or target in whole_candidate[term],
                            'trie_mapping': target in runtime[term],
                            'whole_candidate_mapping': target in whole_candidate[term]},
                'lua': {tier: {'status': 'reachable' if contains(actual[tier], target) else 'not_emitted',
                               'suffix': actual[tier]} for tier in TIERS},
                'pinyin_candidate': observation['pinyin_candidate'] if observation else {'status': 'unverified'},
                'native_preview': ({'status': 'passed' if contains(observation['suffix'], target) else 'not_emitted',
                                    'comment': observation['comment']} if observation and observation['pinyin_candidate']['status'] == 'found'
                                   else {'status': 'unverified'}),
                'native_commit': ({'status': 'passed' if contains(observation['commit'], target) else 'not_emitted',
                                   'text': observation['commit']} if observation and observation['pinyin_candidate']['status'] == 'found'
                                  else {'status': 'unverified'}),
            })
        reachable = {tier: [p['term'] for p in probes if p['lua'][tier]['status'] == 'reachable'] for tier in TIERS}
        gaps = []
        if not any(p['natural_name']['status'] == 'reviewed' for p in probes):
            gaps.append('natural_name_unverified')
        if any(p['natural_name']['status'] == 'reviewed' and not p['lexicon']['tier_mapping'] for p in probes):
            gaps.append('reviewed_entry_missing_from_tier')
        if any(p['natural_name']['status'] == 'reviewed' and p['lua']['general']['status'] != 'reachable' for p in probes):
            gaps.append('reviewed_entry_not_emitted_general')
        for tier in TIERS:
            if not reachable[tier]:
                gaps.append('no_' + tier + '_entry')
        if not any(p['pinyin_candidate']['status'] == 'found' for p in probes):
            gaps.append('pinyin_unverified_or_not_found')
        if not any(p['native_commit']['status'] == 'passed' for p in probes):
            gaps.append('native_commit_unverified_or_not_emitted')
        entries.append({'index': number, 'emoji': row['emoji'], 'name_en': row['name_en'],
                        'group': row['group'], 'names': row['names'], 'gaps': gaps,
                        **({'name_review': name_rows[target]} if natural_names else {}),
                        'frontend_ui_preview': {'status': 'unverified'},
                        'application_insertion': {'status': 'unverified'},
                        'reachable_terms': reachable, 'probes': probes})
    summary = {'base_emoji': len(base), 'skin_variants_excluded': len(inventory)-len(base),
               'unique_terms_executed': len(terms), 'term_target_pairs': sum(len(r['probes']) for r in entries),
               'lua_calls': len(terms)*3,
               'natural_name_reviewed_emoji': sum(any(p['natural_name']['status']=='reviewed' for p in r['probes']) for r in entries),
               'native_pinyin_checked_terms': len(observations)}
    summary['reviewed_terms'] = len(reviews)
    summary['added_terms'] = sum(r['runtime_action'] == 'add' for r in reviews) if not baseline else 0
    summary['deferred_boundary_terms'] = sum(r['runtime_action'] == 'deferred_boundary' for r in reviews)
    summary['frontend_ui_preview_verified_emoji'] = 0
    summary['application_insertion_verified_emoji'] = 0
    summary['pinyin_candidate_found_terms'] = sum(r['pinyin_candidate']['status'] == 'found' for r in observations.values())
    summary['added_terms_native_commit_passed'] = sum(
        r['runtime_action'] == 'add' and r['term'] in observations
        and all(contains(observations[r['term']]['commit'], target) for target in r['targets'])
        for r in reviews)
    for tier in TIERS:
        summary['zero_' + tier + '_entry'] = sum(not r['reachable_terms'][tier] for r in entries)
        if natural_names:
            summary['zero_reviewed_name_' + tier + '_entry'] = sum(
                not any(p['natural_name']['status'] == 'reviewed' and p['lua'][tier]['status'] == 'reachable'
                        for p in r['probes']) for r in entries)
    if natural_names:
        summary['reviewed_name_target_pairs'] = sum(len(r['names']) for r in name_rows.values())
        summary['pinyin_reviewed_name_target_pairs'] = len({(r['selected_term'], normalize(t))
            for r in validate_reviews(root) for t in r['targets']})
        summary['zero_reviewed_name_tier_mapping'] = sum(
            not any(p['natural_name']['status'] == 'reviewed' and p['lexicon']['tier_mapping']
                    for p in r['probes']) for r in entries)
    for layer in ('pinyin_candidate', 'native_preview', 'native_commit'):
        summary[layer + '_passed_emoji'] = sum(any(p[layer]['status'] in ('found','passed') for p in r['probes']) for r in entries)
    paths = [str(p.relative_to(root)) for p in sorted((root/'data').glob('*.json'))]
    paths += ['data/relation_reviews.jsonl']
    if natural_names:
        paths += ['data/natural_name_review/decisions.psv', 'data/natural_name_review/policy.json']
        paths += ['data/pinyin_entry_review/'+name for name in
                  ('decisions.psv','reviews.json','mapping_additions.json','supplement.json')]
    paths += [str(p.relative_to(root)) for p in sorted((root/'rime/lua/shi_emoji').glob('*.lua'))]
    metadata = {'format_version': 1, 'baseline_release': 'v0.1.0-alpha.4',
                'phase': 'alpha4-baseline' if baseline else ('pinyin-entry-repairs' if natural_names else 'current'),
                'scope': 'isolated complete input; actual Lua, default skin, neutral gender, adult=false',
                'native_scope': (native or {}).get('scope', 'unverified'),
                'sources_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}}
    metadata['sources_sha256']['rime/lua/shi_emoji/tier_data.lua'] = hashlib.sha256(compiled.encode()).hexdigest()
    return {'metadata': metadata, 'summary': summary, 'entries': entries}


def write_report(report, output):
    output.mkdir(parents=True, exist_ok=True)
    (output/'summary.json').write_text(json.dumps({k:v for k,v in report.items() if k!='entries'}, ensure_ascii=False, indent=2)+'\n')
    encoded = ''.join(json.dumps(r, ensure_ascii=False, separators=(',',':'))+'\n' for r in report['entries']).encode()
    (output/'entries.jsonl.gz').write_bytes(gzip.compress(encoded, mtime=0))
    lines = ['index\temoji\tnames\tstrict_entries\tgeneral_entries\tdivergent_entries\treviewed_names\treviewed_names_missing_from_tier\tinventory_names_not_emitted_general\tgaps']
    for row in report['entries']:
        reviewed = [p for p in row['probes'] if p['natural_name']['status'] == 'reviewed']
        lines.append('\t'.join([str(row['index']), row['emoji'], '/'.join(row['names'])] +
                              [' / '.join(row['reachable_terms'][tier]) for tier in TIERS] +
                              [' / '.join(p['term'] for p in reviewed),
                               ' / '.join(p['term'] for p in reviewed if not p['lexicon']['tier_mapping']),
                               ' / '.join(p['term'] for p in row['probes'] if 'inventory_name' in p['sources'] and p['lua']['general']['status'] != 'reachable'),
                               ','.join(row['gaps'])]))
    (output/'entries.tsv').write_text('\n'.join(lines)+'\n')
    if 'name_review' in report['entries'][0]:
        lines = ['index\temoji\tselected_names\tmissing_tier_mapping\tnot_emitted_general\tgeneral_reachable_names\tusage\tnative_status']
        for row in report['entries']:
            selected = [p for p in row['probes'] if p['natural_name']['status'] == 'reviewed']
            lines.append('\t'.join([str(row['index']), row['emoji'],
                '/'.join(p['term'] for p in selected),
                '/'.join(p['term'] for p in selected if not p['lexicon']['tier_mapping']),
                '/'.join(p['term'] for p in selected if p['lua']['general']['status'] != 'reachable'),
                '/'.join(p['term'] for p in selected if p['lua']['general']['status'] == 'reachable'),
                row['name_review']['names'][0]['usage'], 'unverified']))
        (output/'name-gaps.tsv').write_text('\n'.join(lines)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native', type=Path)
    parser.add_argument('--natural-names', action='store_true', help='Include all 1906 individual natural-name reviews')
    parser.add_argument('--baseline', action='store_true', help='Rebuild alpha.4 table without common-entry additions in a temporary directory')
    args = parser.parse_args()
    if args.baseline and args.native:
        parser.error('Baseline must not borrow current native evidence')
    if args.natural_names and (args.baseline or args.native):
        parser.error('Full name review records current Lua only; do not borrow historical native/baseline evidence')
    report = analyze(native=json.loads(args.native.read_text()) if args.native else None, baseline=args.baseline,
                     natural_names=args.natural_names)
    write_report(report, args.output)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
