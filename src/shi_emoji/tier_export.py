"""Compile reviewed relations into a compact runtime table, without review metadata."""
from collections import defaultdict
import json
from pathlib import Path

from .datafiles import merged_data
from .export import lua_value

LEVEL = {"strict": 1, "general": 2, "divergent": 3}


SENTENCE_SCOPE = {
    "whole_token": "token",
    "whole_candidate_only": False,
    "requires_disambiguation": False,
}


def sentence_scopes(directory, rows):
    expected = {row["id"]: row for row in rows
                if row["status"] == "approved" and row["scope_review"]["code"] == "C"}
    decisions = {}
    for batch in sorted((directory / "sentence_scope_review").glob("batch-[0-9][0-9][0-9].jsonl")):
        for line in batch.read_text().splitlines():
            proposal = json.loads(line)
            relation_id = proposal["id"]
            row = expected[relation_id]
            assert relation_id not in decisions, relation_id
            assert all(proposal[key] == row[key] for key in
                       ("expression", "target", "min_tier", "core_index")), relation_id
            scope = SENTENCE_SCOPE[proposal["decision"]]
            if scope == "token":
                assert proposal["condition_spec"] == ["verified_token_boundary", "asserted_mention"], relation_id
            decisions[relation_id] = scope
    assert decisions.keys() == expected.keys(), "Sentence-scope review does not cover the approved C relations"
    return decisions


def compile_rules(directory, include_common=True, *, content_gate="normal"):
    directory = Path(directory)
    legacy = merged_data(directory / "phrases.json")
    source = (legacy if content_gate == "normal" else
              json.loads((directory / "adult_phrases.json").read_text()))
    orders = {phrase: r["emoji"] for r in source["rules"] for phrase in r["phrases"]}
    aliases = json.loads((directory / "traditional_aliases.json").read_text())["aliases"]
    by_phrase = defaultdict(dict)
    expressions = set()
    rows = [json.loads(line) for line in (directory / "relation_reviews.jsonl").read_text().splitlines()]
    scopes = sentence_scopes(directory, rows)
    for row in rows:
        phrase, target = row["expression"], row["target"]
        expressions.add(phrase)
        if (row["status"] != "approved" or row["semantic_review"]["status"] != "rechecked"
                or row["content_gate"] != content_gate):
            continue
        scope = row["scope_review"]["code"]
        assert scope in ("W", "C", "F"), row["id"]
        order = orders.get(phrase, [])
        entry = [target, LEVEL[row["min_tier"]], scopes[row["id"]] if scope == "C" else scope == "W",
                 row["target_spec"]["kind"] == "fixed_sequence"]
        rank = (entry[1], order.index(target) if target in order else len(order), target)
        key = target.replace("\ufe0f", "")
        if key not in by_phrase[phrase] or rank < by_phrase[phrase][key][0]:
            by_phrase[phrase][key] = (rank, entry)
    rules = {p: [entry for _, entry in sorted(entries.values())]
             for p, entries in sorted(by_phrase.items())}
    if include_common and content_gate == "normal":
        # Separately reviewed natural entry names: exact candidates only. Keep
        # every existing relation and its tier/scope; give new literal names
        # priority over broader interpretations without changing composition.
        common = json.loads((directory / "common_entry_reviews.json").read_text())
        valid = {r['emoji'].replace('\ufe0f', '') for r in
                 json.loads((directory / 'emoji_inventory.json').read_text())
                 if not r['skin_variant']}
        for row in common['entries']:
            if row['runtime_action'] == 'deferred_boundary':
                continue
            assert row['runtime_action'] == 'add', row['term']
            phrase = row['term']
            existing = rules.get(phrase, [])
            keys = {entry[0].replace('\ufe0f', '') for entry in existing}
            added = []
            for target in row['targets']:
                key = target.replace('\ufe0f', '')
                assert key in valid and key not in keys, (phrase, target)
                keys.add(key)
                added.append([target, 1, False, False])
            rules[phrase] = added + existing
    for alias, source in sorted(aliases.items()):
        if alias not in expressions and source in rules:
            rules[alias] = rules[source]
    return rules


def runtime_source(rules):
    return "-- Generated from the reviewed core relations. See THIRD_PARTY_NOTICES.md.\nreturn " + lua_value(rules) + "\n"


def compile_entry_rules(directory, include_pinyin=True):
    """Exact-candidate overlay; intentionally never added to the substring trie."""
    directory = Path(directory)
    base = compile_rules(directory)
    repairs = json.loads((directory / 'entry_repairs_262.json').read_text())
    result = {}
    additions = json.loads((directory/'pinyin_entry_review/mapping_additions.json').read_text())['entries'] if include_pinyin else []
    for row in repairs['entries'] + repairs['preservation_entries'] + additions:
        term = row['term']
        existing = base.get(term, [])
        levels = {e[0].replace('\ufe0f', ''): e[1] for e in existing}
        targets = [[target, levels.get(target.replace('\ufe0f', ''), LEVEL[row['min_tier']])]
                   for target in row['targets']]
        minimum = min(e[1] for e in targets)
        seen = {e[0].replace('\ufe0f', '') for e in targets}
        for target, tier, _, sequence in existing:
            assert not sequence, term
            if target.replace('\ufe0f', '') not in seen:
                targets.append([target, tier])
                seen.add(target.replace('\ufe0f', ''))
        priority = repairs['ranking'].get(term)
        if priority:
            order = {target.replace('\ufe0f', ''): i for i, target in enumerate(priority)}
            targets.sort(key=lambda e: order.get(e[0].replace('\ufe0f', ''), len(order)))
        result[term] = {'min_tier': minimum, 'targets': targets}
    strict = json.loads((directory / "strict_entry_reviews.json").read_text())
    assert strict["scope"] == "whole_candidate" and strict["min_tier"] == "strict"
    primary = defaultdict(list)
    for row in strict["entries"]:
        for term in [row["term"], *row.get("traditional", [])]:
            primary[term].append(row["target"])
    for term, targets in primary.items():
        previous = result.get(term)
        if previous:
            alternatives = previous["targets"]
        else:
            existing = base.get(term, [])
            assert not any(entry[3] for entry in existing), term
            alternatives = [entry[:2] for entry in existing]
        keys = {target.replace("\ufe0f", "") for target in targets}
        assert len(keys) == len(targets), term
        result[term] = {
            "min_tier": LEVEL["strict"],
            "targets": [[target, LEVEL["strict"]] for target in targets] + [
                entry for entry in alternatives if entry[0].replace("\ufe0f", "") not in keys
            ],
        }
    return result


def entry_runtime_source(rules):
    return '-- Reviewed whole-candidate names; never used as sentence substrings.\nreturn ' + lua_value(rules) + '\n'


def match_metadata_source(directory):
    data = merged_data(Path(directory) / "phrases.json")
    metadata = {key: data[key] for key in ("word_guards", "boundaries", "negators")}
    return "-- Shared matching metadata without legacy mappings. See THIRD_PARTY_NOTICES.md.\nreturn " + lua_value(metadata) + "\n"


if __name__ == "__main__":
    rules = compile_rules("data")
    Path("rime/lua/shi_emoji/tier_data.lua").write_text(runtime_source(rules), encoding="utf-8")
    print(f"Exported {len(rules)} tiered expressions and aliases")
    adult = compile_rules("data", content_gate="adult")
    Path("rime/lua/shi_emoji/adult.lua").write_text(runtime_source(adult), encoding="utf-8")
    print(f"Exported {len(adult)} separately gated expressions")
    entries = compile_entry_rules('data')
    Path('rime/lua/shi_emoji/entry_data.lua').write_text(entry_runtime_source(entries), encoding='utf-8')
    print(f'Exported {len(entries)} exact candidate entries')
    Path("rime/lua/shi_emoji/match_metadata.lua").write_text(match_metadata_source("data"), encoding="utf-8")
