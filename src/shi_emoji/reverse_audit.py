"""Audit whether each base Emoji can be found by entering its mapped terms alone.

This is a matcher-level reachability check, not a Rime candidate or semantic
quality benchmark. Source terms are rebuilt from pinned data in memory.
"""
import argparse
import json
from pathlib import Path

from .coverage import audit, inventory, normalize
from .datafiles import merged_data
from .match import Matcher


ROOT = Path(__file__).resolve().parents[2]


def analyze(rows, data):
    report = audit(rows, data)
    matcher = Matcher(data)
    rules = {rule["phrases"][0]: rule for rule in data["rules"]}
    entries = []
    for row in report["entries"]:
        if row["skin_variant"]:
            continue
        target = normalize(row["emoji"])
        reachable, blocked_by_length = [], []
        for term in row["terms"]:
            rule = rules[term]
            if len(term) < rule.get("min_context_len", 0):
                blocked_by_length.append(term)
            candidates = matcher.search(term)["candidates"]
            if any(normalize(candidate["emoji"]) == target for candidate in candidates):
                reachable.append(term)
        entries.append({"emoji": row["emoji"], "name_en": row["name_en"],
                        "group": row["group"], "names": row["names"],
                        "term_count": len(row["terms"]), "reachable_terms": reachable,
                        "blocked_by_length": blocked_by_length})
    summary = {"base_emoji": len(entries),
               "zero_reachable": sum(not row["reachable_terms"] for row in entries),
               "under_three_reachable": sum(len(row["reachable_terms"]) < 3 for row in entries),
               "zero_lexical_terms": report["summary"]["zero_terms"],
               "under_three_lexical_terms": report["summary"]["under_three"]}
    return {"summary": summary, "entries": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-reachable", type=int, default=0,
                        help="Only show Emoji with at most this many standalone reachable terms")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    if args.max_reachable < 0 or args.limit < 0:
        parser.error("--max-reachable and --limit must be nonnegative")
    data = merged_data(ROOT / "data/phrases.json", include_traditional=False)
    result = analyze(inventory(ROOT), data)
    selected = [row for row in result["entries"]
                if len(row["reachable_terms"]) <= args.max_reachable]
    selected.sort(key=lambda row: (len(row["reachable_terms"]), row["group"], row["name_en"]))
    print(json.dumps({"summary": result["summary"], "matching_entries": len(selected),
                      "entries": selected[:args.limit]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
