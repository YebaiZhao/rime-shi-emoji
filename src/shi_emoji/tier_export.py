"""Compile reviewed relations into a compact runtime table, without review metadata."""
from collections import defaultdict
import json
from pathlib import Path

from .datafiles import merged_data
from .export import lua_value

LEVEL = {"strict": 1, "general": 2, "divergent": 3}


def compile_rules(directory):
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
    for alias, source in sorted(aliases.items()):
        if alias not in expressions and source in rules:
            rules[alias] = rules[source]
    return rules


def runtime_source(rules):
    return "-- Generated from the reviewed core relations. See THIRD_PARTY_NOTICES.md.\nreturn " + lua_value(rules) + "\n"


if __name__ == "__main__":
    rules = compile_rules("data")
    Path("rime/lua/shi_emoji/tier_data.lua").write_text(runtime_source(rules), encoding="utf-8")
    print(f"Exported {len(rules)} tiered expressions and aliases")
