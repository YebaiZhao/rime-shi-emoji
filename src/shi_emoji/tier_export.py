"""Compile reviewed relations into a compact runtime table, without review metadata."""
from collections import defaultdict
import json
from pathlib import Path

from .datafiles import merged_data
from .export import lua_value

LEVEL = {"strict": 1, "general": 2, "divergent": 3}


def compile_rules(directory, include_common=True):
    directory = Path(directory)
    legacy = merged_data(directory / "phrases.json")
    orders = {r["phrases"][0]: r["emoji"] for r in legacy["rules"]}
    aliases = json.loads((directory / "traditional_aliases.json").read_text())["aliases"]
    by_phrase = defaultdict(dict)
    expressions = set()
    for line in (directory / "relation_reviews.jsonl").read_text().splitlines():
        row = json.loads(line)
        phrase, target = row["expression"], row["target"]
        expressions.add(phrase)
        if (row["status"] != "approved" or row["semantic_review"]["status"] != "rechecked"
                or row["content_gate"] != "normal"):
            continue
        scope = row["scope_review"]["code"]
        assert scope in ("W", "C", "F"), row["id"]
        order = orders.get(phrase, [])
        entry = [target, LEVEL[row["min_tier"]], scope == "W",
                 row["target_spec"]["kind"] == "fixed_sequence"]
        rank = (entry[1], order.index(target) if target in order else len(order), target)
        key = target.replace("\ufe0f", "")
        if key not in by_phrase[phrase] or rank < by_phrase[phrase][key][0]:
            by_phrase[phrase][key] = (rank, entry)
    rules = {p: [entry for _, entry in sorted(entries.values())]
             for p, entries in sorted(by_phrase.items())}
    if include_common:
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


def compile_entry_rules(directory):
    """Exact-candidate overlay; intentionally never added to the substring trie."""
    directory = Path(directory)
    base = compile_rules(directory)
    repairs = json.loads((directory / 'entry_repairs_262.json').read_text())
    result = {}
    for row in repairs['entries'] + repairs['preservation_entries']:
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
    entries = compile_entry_rules('data')
    Path('rime/lua/shi_emoji/entry_data.lua').write_text(entry_runtime_source(entries), encoding='utf-8')
    print(f'Exported {len(entries)} exact candidate entries')
    Path("rime/lua/shi_emoji/match_metadata.lua").write_text(match_metadata_source("data"), encoding="utf-8")
