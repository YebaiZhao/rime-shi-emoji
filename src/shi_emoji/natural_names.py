"""Compile explicit per-item name judgments; never export them into runtime rules."""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path

from .coverage import normalize

ROOT = Path(__file__).resolve().parents[2]
USAGE = {'C': 'everyday', 'D': 'descriptive', 'T': 'specialist', 'P': 'proper_name'}
USAGE_REASON = {
    'C': '采用日常可理解的对象、动作或表情称呼；常用程度为语言判断，没有用户词频测量。',
    'D': '采用保留外形、性别、方向或组合差异的自然描述；未认定存在独有的常用短名。',
    'T': '保留专业或文化领域名称；不为提高覆盖率把泛词硬定为本义。',
    'P': '采用固定清单对象的中文专名；不将专名等同日常高频词，不判断现行政区或旗帜法律状态。',
}


def build_reviews(root=ROOT):
    data = root/'data'
    inventory_path = data/'emoji_inventory.json'
    previous_path = data/'common_entry_reviews.json'
    decision_path = data/'natural_name_review/decisions.psv'
    policy = json.loads((data/'natural_name_review/policy.json').read_text())
    assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == policy['inventory_sha256'], 'Inventory index changed'
    assert hashlib.sha256(previous_path.read_bytes()).hexdigest() == policy['previous_review_sha256'], 'Reconcile the first 15 reviewed Emoji before rebuilding'
    base = [r for r in json.loads(inventory_path.read_text()) if not r['skin_variant']]
    assert len(base) == 1906
    previous = defaultdict(list)
    for row in json.loads(previous_path.read_text())['entries']:
        for target in row['targets']:
            previous[normalize(target)].append(row)
    assert len(previous) == 15
    decisions = {}
    for line_no, line in enumerate(decision_path.read_text().splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        fields = line.split('|')
        assert len(fields) == 4, (line_no, fields)
        number, usage, selected, note = fields
        number = int(number)
        assert number not in decisions and 1 <= number <= 1906, number
        assert usage in USAGE and selected, number
        source = base[number-1]
        assert normalize(source['emoji']) not in previous, number
        if selected == '=':
            terms = source['names']
        elif selected == '@':
            assert usage == 'P' and source['subgroup'] == 'country-flag', number
            assert len(source['names']) == 1 and source['names'][0].startswith('旗: '), number
            name = source['names'][0].removeprefix('旗: ')
            terms = [name, name+'旗']
        else:
            terms = selected.split('/')
        assert terms and len(terms) == len(set(terms)), number
        assert all(t.strip() == t and t and any('\u3400' <= c <= '\u9fff' for c in t) for t in terms), number
        decisions[number] = {'usage': USAGE[usage], 'terms': terms,
                             'rationale': note or USAGE_REASON[usage],
                             'decision_source': {'path': str(decision_path.relative_to(root)), 'line': line_no}}
    expected = {i for i,r in enumerate(base,1) if normalize(r['emoji']) not in previous}
    assert set(decisions) == expected and len(decisions) == 1891, 'Missing or unexpected individual decisions'
    result = []
    for i, source in enumerate(base, 1):
        prior = previous.get(normalize(source['emoji']))
        if prior:
            names = [{'term': r['term'], 'usage': 'prior_review', 'rationale': r['rationale'],
                      'runtime_action': r['runtime_action']} for r in prior]
            decision_source = {'path': 'data/common_entry_reviews.json', 'target': source['emoji']}
            round_name = 'first_batch'
        else:
            decision = decisions[i]
            names = [{'term': t, 'usage': decision['usage'], 'rationale': decision['rationale'],
                      'runtime_action': 'review_only'} for t in decision['terms']]
            decision_source = decision['decision_source']
            round_name = 'remaining_1891'
        result.append({'index': i, 'emoji': source['emoji'], 'name_en': source['name_en'],
                       'group': source['group'], 'inventory_names': source['names'],
                       'status': 'reviewed', 'reviewer': 'Codex',
                       'review_method': 'individual_model_judgment', 'round': round_name,
                       'names': names, 'decision_source': decision_source,
                       'inventory_names_not_selected': [t for t in source['names'] if t not in {n['term'] for n in names}],
                       'scope': 'name_review_only; no tier, sentence-scope, frequency, or input-reachability approval'})
    by_term = defaultdict(list)
    for row in result:
        for name in row['names']:
            by_term[name['term']].append(row['emoji'])
    for row in result:
        for name in row['names']:
            name['shared_with'] = [e for e in by_term[name['term']] if e != row['emoji']]
    return result


def write_reviews(root=ROOT):
    rows = build_reviews(root)
    output = root/'data/natural_name_review'
    (output/'reviews.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',',':'))+'\n' for r in rows))
    lines = ['index\temoji\tname_en\tinventory_names\tselected_names\tusage\treview_round\trationale']
    for r in rows:
        lines.append('\t'.join([str(r['index']), r['emoji'], r['name_en'], '/'.join(r['inventory_names']),
                                '/'.join(n['term'] for n in r['names']), r['names'][0]['usage'], r['round'],
                                '；'.join(dict.fromkeys(n['rationale'] for n in r['names']))]))
    (output/'reviews.tsv').write_text('\n'.join(lines)+'\n')
    counts = Counter(r['names'][0]['usage'] for r in rows)
    summary = {'base_emoji': 1906, 'previous_reviewed': 15, 'newly_reviewed': 1891,
               'reviewed': len(rows), 'pending': 0,
               'name_target_pairs': sum(len(r['names']) for r in rows),
               'unique_names': len({n['term'] for r in rows for n in r['names']}),
               'emoji_by_usage': dict(sorted(counts.items())),
               'new_reviews_with_review_only_scope': 1891,
               'source_sha256': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in [
                   'data/emoji_inventory.json', 'data/common_entry_reviews.json',
                   'data/natural_name_review/decisions.psv', 'data/natural_name_review/policy.json']}}
    (output/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        actual = [json.loads(l) for l in (ROOT/'data/natural_name_review/reviews.jsonl').read_text().splitlines()]
        assert actual == build_reviews(), 'Review projection is stale'
        print('1906 individual reviews current; 1891 new + 15 carried forward')
    else:
        print(json.dumps(write_reviews(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
