"""Reproduce the 174 individual decisions and optional Chinese-name supplement."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .export import lua_value

ROOT = Path(__file__).resolve().parents[2]


def compile_pinyin_entries(root=ROOT):
    directory = root/'data/pinyin_entry_review'
    supplement = json.loads((directory/'supplement.json').read_text())
    before = directory/'selected_before_native.json'
    assert hashlib.sha256(before.read_bytes()).hexdigest() == supplement['baseline_sha256']
    expected = {r['term'] for r in json.loads(before.read_text())['entries']
                if r['pinyin_candidate']['status'] != 'found'}
    assert {r['term'] for r in supplement['entries']} == expected
    strict_names = json.loads((root/'data/strict_entry_reviews.json').read_text())['entries']
    result = defaultdict(list)
    for row in supplement['entries'] + [row for row in strict_names if 'pinyin' in row]:
        key = row['pinyin']
        assert key.isascii() and key.isalpha() and key.islower(), row['term']
        if row['term'] not in result[key]:
            result[key].append(row['term'])
    return dict(result)


def pinyin_source(entries):
    return '-- Reviewed full-pinyin Chinese names; opt-in translator only.\nreturn ' + lua_value(entries) + '\n'


def validate_reviews(root=ROOT):
    directory = root/'data/pinyin_entry_review'
    original = root/'data/reachability/entry-repairs-262/native.json'
    review = json.loads((directory/'reviews.json').read_text())
    assert hashlib.sha256(original.read_bytes()).hexdigest() == review['baseline_sha256']
    missing = [r for r in json.loads(original.read_text())['entries'] if not r['commit_passed']]
    decisions = [line.split('|') for line in (directory/'decisions.psv').read_text().splitlines()]
    assert len(missing) == len(decisions) == len(review['reviews']) == 174
    for index, (prior, decision, row) in enumerate(zip(missing, decisions, review['reviews']), 1):
        number, term, reason = decision
        assert index == int(number) == row['index']
        assert prior['term'] == row['original_term'] and prior['targets'] == row['targets']
        assert term == row['selected_term'] and reason == row['rationale']
        assert ''.join(row['syllables']).lower() == row['pinyin']
    return review['reviews']


if __name__ == '__main__':
    validate_reviews()
    rules = compile_pinyin_entries()
    (ROOT/'rime/lua/shi_emoji/pinyin_data.lua').write_text(pinyin_source(rules))
    print(f'Exported {sum(map(len, rules.values()))} optional Chinese names')
