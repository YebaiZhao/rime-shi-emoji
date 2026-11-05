"""Rebuild/check core review data from versionable decisions; no runtime deployment.

Initial decisions are historical, not semantic acceptance. Revisions retain their
before/after decisions. Pending sentence scopes cannot authorize runtime use.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/relation_review'
OUTPUT = ROOT / 'data/relation_reviews.jsonl'
PROGRESS = ROOT / 'data/relation_review_progress.json'


def read_json(path):
    return json.loads(path.read_text())


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def write_lines(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


def read_gzip(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def current_reviews():
    reviews = read_lines(DATA / 'standard3_reviews.jsonl')
    assert len({r['id'] for r in reviews}) == len(reviews)
    assert all(r['standard_id'] == read_json(DATA / 'policy.json')['standard_id'] for r in reviews)
    discussions = {r['core_index']: r for r in reviews if r['after']['status'] == 'needs_discussion'}
    handled = set()
    for line in (DATA / 'discussion_resolutions.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        indices, decision, scope, reason = line.split('\t', 3)
        assert reason.strip()
        for index in map(int, indices.split()):
            assert index not in handled, index
            handled.add(index)
            review = discussions[index]
            if decision.startswith('Q:'):
                assert scope == 'Q'
                review['discussion_category'] = decision.removeprefix('Q:')
                review['discussion_reason'] = reason
                continue
            assert ((decision == 'excluded' and scope == 'N') or
                    (decision in ('strict', 'general', 'divergent') and scope in ('F', 'W', 'C')))
            review['after'] = {'status': 'excluded' if scope == 'N' else 'approved',
                               'min_tier': None if scope == 'N' else decision,
                               'rationale': reason}
            review['scope_code'] = scope
            review['scope_reason'] = reason
            review['semantic_review'] = 'rechecked'
    assert handled == set(discussions), 'discussion resolution coverage differs'
    return {r['id']: r for r in reviews}


def scope_fields(row, code, reason):
    applicable = (['whole_candidate', 'whole_token'] if code == 'W' else
                  ['whole_candidate'] if code in ('F', 'C') else [])
    conditions = {
        'whole_candidate': {'predicate': 'exact_candidate', 'expression_ref': row['id']},
        'whole_token': {'predicate': 'verified_token_boundary', 'expression_ref': row['id'],
                        'implementation_validation': 'not_run'},
    }
    return applicable, {
        'code': code,
        'status': 'reviewed_specification' if code in ('W', 'F') else
                  'partial_sentence_pending' if code == 'C' else
                  'pending_stage_three' if code == 'P' else 'not_applicable',
        'sentence_authorization': 'specification_approved_runtime_pending' if code == 'W' else
                                  'pending_stage_three' if code in ('C', 'P') else 'denied',
        'reason': reason,
        'conditions': {unit: conditions[unit] for unit in applicable},
        'context_disambiguation': {
            'status': 'pending_stage_three' if code in ('C', 'P', 'Q') else 'not_required_for_specified_scope',
            'reason': reason if code in ('C', 'P', 'Q') else None,
            'executable_predicate': None,
        },
        'content_gate': row['content_gate'],
        'emit_target_intact': True,
        'combination': row['target_spec']['kind'] == 'fixed_sequence',
    }


def rebuild_rows():
    with gzip.open(DATA / 'initial_decisions.jsonl.gz', 'rt') as stream:
        rows = [json.loads(line) for line in stream]
    targets = read_json(DATA / 'targets.json')
    for event in read_lines(DATA / 'revisions.jsonl'):
        r = rows[event['core_index'] - 1]
        assert event['before'] == {k: r[k] for k in event['before']}, event['core_index']
        r.update(event['after'])
    reviews = current_reviews()
    norm = read_json(DATA / 'expression_normalization.json')
    key = lambda r: (norm.get(r['expression'], r['expression']), r['target'].replace('\ufe0f', ''))
    equivalents = {}
    for review in reviews.values():
        before = rows[review['core_index'] - 1]
        assert review['before'] == {k: before[k] for k in review['before']}, review['core_index']
        signature = review['after']['status'], review['after']['min_tier']
        group = key(before)
        if group in equivalents:
            assert signature == equivalents[group]['signature'], ('reviewed normalization conflict', group)
        equivalents[group] = {'signature': signature, 'review': review}
    for r in rows:
        r['target_spec'] = targets[r['target']]
        review = reviews.get(r['id'])
        r['semantic_review'] = {
            'status': review['semantic_review'] if review else 'pending',
            'standard_id': read_json(DATA / 'policy.json')['standard_id'],
            'revision_batch': review['batch'] if review else None,
            'derived_from': None,
        }
        if review:
            r.update(review['after'])
            code, reason = review['scope_code'], review['scope_reason']
        elif key(r) in equivalents:
            base = equivalents[key(r)]['review']
            r.update(base['after'])
            r['semantic_review']['derived_from'] = base['id']
            code = 'P'
            reason = '简繁或显示变体依据基关系同步结论；此项仍未逐项复核，不计入完成，句中范围待审。'
        else:
            code = 'P'
            reason = '本次确认标准尚未逐项复核此关系；历史分级保留供对照，未授予适用范围。'
        r['applicability'], r['scope_review'] = scope_fields(r, code, reason)
        r['runtime_eligible'] = False
        r['runtime_validation'] = 'not_run'
    return rows


def check(rows):
    assert len(rows) == 11937
    assert [r['core_index'] for r in rows] == list(range(1, 11938))
    assert len({r['id'] for r in rows}) == 11937
    assert len({(r['expression'], r['target']) for r in rows}) == 11937
    sources = {p: read_json(ROOT / p)['rules'] for p in (
        'data/phrases.json', 'data/lexical_phrases.json',
        'data/model_phrases.json', 'data/adult_phrases.json')}
    expected = set()
    for rules in sources.values():
        for rule in rules:
            targets = rule['emoji'] + ([rule['suffix']] if rule.get('suffix') else [])
            expected.update((phrase, target) for phrase in rule['phrases'] for target in targets)
    assert {(r['expression'], r['target']) for r in rows} == expected, 'source coverage differs'
    norm = read_json(DATA / 'expression_normalization.json')
    reviews = current_reviews()
    assert set(reviews) <= {r['id'] for r in rows}
    for row in rows:
        if row['id'] in reviews:
            review = reviews[row['id']]
            assert review['core_index'] == row['core_index']
            assert review['sources'] == row['sources']
            assert {k: row[k] for k in review['after']} == review['after']
            assert row['scope_review']['code'] == review['scope_code']
    signatures = defaultdict(set)
    scope_signatures = defaultdict(set)
    for r in rows:
        assert r['id'] == hashlib.sha256((r['expression'] + '\0' + r['target']).encode()).hexdigest()[:20]
        approved = r['status'] == 'approved'
        assert r['status'] in ('approved', 'excluded', 'needs_discussion')
        assert (r['min_tier'] in ('strict', 'general', 'divergent')) == approved
        assert r['rationale'] and r['sources']
        for s in r['sources']:
            rule = sources[s['path']][s['rule_index']]
            assert r['expression'] in rule['phrases']
            assert s['role'] in ('emoji', 'fixed_sequence')
            assert (r['target'] in rule['emoji'] if s['role'] == 'emoji' else r['target'] == rule.get('suffix'))
        gate = 'adult' if any(s['path'] == 'data/adult_phrases.json' for s in r['sources']) else 'normal'
        assert r['content_gate'] == gate
        spec = r['target_spec']
        assert ''.join(spec['items']) == r['target'] and spec['raw_unicode_preserved']
        assert (spec['kind'] == 'fixed_sequence') == (len(spec['items']) > 1)
        assert spec['kind'] in ('fixed_sequence', 'single_emoji', 'text_symbol')
        scope = r['scope_review']
        assert scope['code'] in ('W', 'F', 'C', 'P', 'N', 'Q')
        assert scope['reason']
        assert (r['applicability'], scope) == scope_fields(r, scope['code'], scope['reason'])
        reviewed = r['semantic_review']['status'] != 'pending'
        if reviewed:
            assert (scope['code'] in ('W', 'F', 'C')) == approved
            assert (scope['code'] == 'Q') == (r['status'] == 'needs_discussion')
            assert (scope['code'] == 'N') == (r['status'] == 'excluded')
        else:
            assert scope['code'] == 'P' and not r['applicability']
        assert r['semantic_review']['status'] in ('pending', 'rechecked', 'needs_discussion')
        assert r['semantic_review']['standard_id'] == read_json(DATA / 'policy.json')['standard_id']
        assert r['entry_access'] == 'phase_three_pending'
        assert r['runtime_validation'] == 'not_run' and r['runtime_eligible'] is False
        signatures[norm.get(r['expression'], r['expression']), r['target'].replace('\ufe0f', '')].add((r['status'], r['min_tier']))
        if reviewed:
            scope_signatures[norm.get(r['expression'], r['expression']), r['target'].replace('\ufe0f', '')].add(scope['code'])
    assert not [(key, values) for key, values in signatures.items() if len(values) > 1], 'normalization conflicts'
    assert all(len(values) == 1 for values in scope_signatures.values()), 'reviewed normalization scope conflicts'
    index = {(r['expression'], r['target'].replace('\ufe0f', '')): r for r in rows}
    for expression, target in read_json(DATA / 'policy.json')['regression_cases']:
        assert index[expression, target.replace('\ufe0f', '')]['status'] == 'excluded'
    for case in read_json(ROOT / 'tests/fixtures/basic_keywords_116.json')['cases']:
        for target in case['expected']:
            assert index[case['query'], target.replace('\ufe0f', '')]['status'] == 'approved'
    # User-authorized keyboard changes legitimately invalidate the historic whole-tree freeze.
    for path, digest in read_json(DATA / 'data_integrity_scope.json')['files'].items():
        source = ROOT / path
        # Upstream build caches are intentionally absent from fresh source checkouts.
        if path.startswith('data/upstream/') and not source.exists():
            continue
        assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, path
    return {
        'core_total': len(rows),
        'initial_decisions_completed': len(rows),
        'semantic_recheck_examined': sum(r['semantic_review']['status'] != 'pending' for r in rows),
        'semantic_recheck_completed': sum(r['semantic_review']['status'] == 'rechecked' for r in rows),
        'semantic_recheck_pending': sum(r['semantic_review']['status'] == 'pending' for r in rows),
        'semantic_needs_discussion': sum(r['semantic_review']['status'] == 'needs_discussion' for r in rows),
        'discussion_categories': dict(Counter(r['discussion_category'] for r in reviews.values()
                                              if 'discussion_category' in r)),
        'scope_pending': sum(r['scope_review']['code'] in ('C', 'P', 'Q') for r in rows),
        'scope_specification_reviewed': sum(r['scope_review']['code'] in ('W', 'F', 'N') for r in rows),
        'scope_codes': dict(Counter(r['scope_review']['code'] for r in rows)),
        'cumulative_decisions': dict(Counter(r['min_tier'] or r['status'] for r in rows)),
        'reviewed_decisions': dict(Counter(r['min_tier'] or r['status'] for r in rows
                                          if r['semantic_review']['status'] != 'pending')),
        'historical_unrevisited_decisions': dict(Counter(r['min_tier'] or r['status'] for r in rows
                                                        if r['semantic_review']['status'] == 'pending')),
        'target_kinds': dict(Counter(r['target_spec']['kind'] for r in rows)),
        'normalization_conflicts': 0,
        'runtime_validation': 'not_run',
        'runtime_eligible': 0,
    }


def build():
    rows = rebuild_rows()
    result = check(rows)
    write_lines(OUTPUT, rows)
    progress = {
        'schema_version': 3, 'scope': 'all_sources_core_first',
        'status': 'revision_incomplete',
        'core_status': ('semantic_decisions_complete' if result['semantic_recheck_completed'] == len(rows)
                        else 'initial_decisions_complete_revision_pending'),
        'core_completed': 11937, 'core_remaining': 0,
        'standard_id': read_json(DATA / 'policy.json')['standard_id'],
        'semantic_acceptance': 'incomplete',
        'semantic_next_index': next((r['core_index'] for r in rows if r['semantic_review']['status'] == 'pending'), None),
        'semantic_recheck_batches': batch_progress(rows),
        'sentence_scope_stage': 3, 'entry_access_stage': 3, 'runtime_implementation_stage': 3,
        'phase_two_full_source_status': 'incomplete',
        'all_source_total': 130820, 'noncore_pending': 118883,
        'all_source_remaining': 130820 - result['semantic_recheck_completed'],
        'all_source_unexamined': 130820 - result['semantic_recheck_examined'],
        'new_relations_added': 0,
        'counting_note': 'examined includes needs_discussion; completed counts decided only; cumulative_decisions includes unaccepted historical labels',
        **result,
    }
    dump(PROGRESS, progress)
    dump(DATA / 'unresolved.json', [r for r in current_reviews().values() if r['after']['status'] == 'needs_discussion'])
    write_source_projection(rows)
    return result


def batch_progress(rows):
    batches = defaultdict(list)
    for r in rows:
        batch = r['semantic_review']['revision_batch']
        if batch:
            batches[batch].append(r)
    reviews = current_reviews()
    return [{'batch': batch, 'range': [min(r['core_index'] for r in group), max(r['core_index'] for r in group)],
             'examined': len(group), 'decided': sum(r['status'] != 'needs_discussion' for r in group),
             'needs_discussion': sum(r['status'] == 'needs_discussion' for r in group),
             'grade_changes': sum((reviews[r['id']]['before']['status'], reviews[r['id']]['before']['min_tier']) !=
                                  (r['status'], r['min_tier']) for r in group),
             'decisions': dict(Counter(r['min_tier'] or r['status'] for r in group))}
            for batch, group in batches.items()]


def source_projection(rows):
    manifest = read_json(DATA / 'source_queue_manifest.json')
    assert hashlib.sha256((DATA / 'source_queue.jsonl.gz').read_bytes()).hexdigest() == manifest['sha256']
    queue = read_gzip(DATA / 'source_queue.jsonl.gz')
    assert len(queue) == 130820 and len({r['id'] for r in queue}) == 130820
    assert [r['queue_index'] for r in queue] == list(range(1, 130821))
    assert sum(r['core_index'] is not None for r in queue) == 11937
    assert sum(len(r['sources']) for r in queue) == 172019
    index = {r['id']: r for r in rows}
    for r in queue:
        if r['id'] in index:
            core = index[r['id']]
            assert r['core_index'] == core['core_index']
            r.update(semantic_status=core['semantic_review']['status'],
                     min_tier=core['min_tier'], decision_status=core['status'],
                     scope_status=core['scope_review']['status'], core_projection_id=core['id'])
    return queue


def write_source_projection(rows):
    queue = source_projection(rows)
    with gzip.GzipFile(str(ROOT / 'data/relation_review_queue.jsonl.gz'), 'wb', mtime=0) as stream:
        for r in queue:
            stream.write((json.dumps(r, ensure_ascii=False) + '\n').encode())


def refresh_legacy():
    """Refresh optional ignored projections. They are never a rebuild input."""
    folder = ROOT / 'dist/tier-phase2-2026-11-04'
    rows = read_lines(OUTPUT)
    index = {r['id']: r for r in rows}
    if (folder / 'review-ledger.jsonl').exists():
        ledger = read_lines(folder / 'review-ledger.jsonl')
        write_lines(folder / 'review-ledger.jsonl', [index.get(r['id'], r) for r in ledger])
    for batch in folder.glob('batch-*'):
        if not (batch / 'output.jsonl').exists():
            continue
        current = [index[r['id']] for r in read_lines(batch / 'output.jsonl')]
        write_lines(batch / 'output.jsonl', current)
        changes_path = batch / 'changes.jsonl'
        if changes_path.exists():
            changes = read_lines(changes_path)
            for entry in changes:
                entry['after'] = index[entry['after']['id']]
                entry['canonical_source'] = 'data/relation_review'
            write_lines(changes_path, changes)
        (batch / 'decisions.tsv').write_text(''.join(
            f"{r['core_index']}\t{r['min_tier'] or r['status']}\t{r['rationale']}\n" for r in current))
        old = read_json(batch / 'summary.json')
        old.update(decisions=dict(Counter(r['min_tier'] or r['status'] for r in current)),
                   semantic_acceptance='revision_incomplete', canonical_source='data/relation_review')
        dump(batch / 'summary.json', old)
    # Historical writers would restore obsolete decisions; retire them explicitly.
    for old in (folder / 'apply_batch.py', folder / 'resolve_batch.py', folder / 'batch-001/build_review.py'):
        if old.exists():
            old.write_text('raise SystemExit("Retired: run python3 scripts/relation_reviews.py build; canonical decisions are in data/relation_review")\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'check', 'refresh-legacy'))
    action = parser.parse_args().action
    if action == 'build':
        result = build()
    elif action == 'check':
        rows = read_lines(OUTPUT)
        assert rows == rebuild_rows(), 'projection differs from canonical decisions'
        result = check(rows)
        progress = read_json(PROGRESS)
        assert all(progress[k] == value for k, value in result.items()), 'progress out of sync'
        assert read_gzip(ROOT / 'data/relation_review_queue.jsonl.gz') == source_projection(rows)
    else:
        refresh_legacy()
        result = {'legacy_projections': 'refreshed'}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
