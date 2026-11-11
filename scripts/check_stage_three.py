"""Audit the shipped strict/general Lua matcher and final display over the full input set."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import tempfile

from shi_emoji.coverage import normalize
from shi_emoji.export import lua_value
from shi_emoji.reachability import ROOT, run_lua
from shi_emoji.tier_export import compile_entry_rules, compile_rules


def observe(terms, runtime, output):
    run_lua(
        "package.path=" + lua_value(str(runtime / "?.lua") + ";") + "..package.path\n"
        "local out=assert(io.open(" + lua_value(str(output)) + ',"w"))\n' +
        "local terms=" + lua_value(terms) + "\n" + r"""
local compose=require('shi_emoji.compose')
local original=compose.suffix
local groups
compose.suffix=function(input, transform)
  for _,group in ipairs(input) do
    local targets={}
    for _,target in ipairs(group.emoji) do
      targets[#targets+1]=transform(target,group.phrase)
    end
    groups[#groups+1]=table.concat({group.phrase,group.start,group.finish,group.level,
        group.negated and transform('🙅',group.phrase) or '',group.suffix or '',
        table.concat(group.emoji,' '),table.concat(targets,' ')},'\t')
  end
  return original(input,transform)
end
local filter=require('shi_emoji.filter')
local settings={skin='default',gender='neutral',adult=true}
for _,term in ipairs(terms) do
  local candidate={text=term,start=0,_end=#term}
  local eligible=filter.eligible(candidate,{input=term})
  for tier=1,2 do
    groups={}
    local suffix=filter.suffix(term,settings,tier) or ''
    out:write(suffix,'\t',#groups,'\t',eligible and '1' or '0','\n')
    for _,group in ipairs(groups) do out:write(group,'\n') end
  end
end
assert(not package.loaded['shi_emoji.adult'], 'adult tier gate')
out:close()
""")


def audit(root, output):
    data = root / "data"
    rules = compile_rules(data)
    overlay = compile_entry_rules(data)
    ledger = [json.loads(line) for line in (data / "relation_reviews.jsonl").read_text().splitlines()]
    inventory = {normalize(row["emoji"]) for row in
                 json.loads((data / "emoji_inventory.json").read_text()) if not row["skin_variant"]}
    excluded = {(row["expression"], normalize(row["target"])) for row in ledger
                if row["status"] == "excluded"}
    terms = sorted(set(rules) | set(overlay) | {row["expression"] for row in ledger})
    totals = {1: Counter(), 2: Counter()}
    reachable = {1: set(), 2: set()}
    with tempfile.TemporaryDirectory(prefix=".shi-stage-three-", dir=output.parent) as directory:
        trace = Path(directory) / "lua.tsv"
        observations = Path(directory) / "observations.jsonl.gz"
        observe(terms, root / "rime/lua", trace)
        with trace.open() as stream, gzip.open(observations, "wt", encoding="utf-8") as report:
            for term in terms:
                results = []
                for tier in (1, 2):
                    suffix, count, eligible = next(stream).rstrip("\n").split("\t")
                    groups = [next(stream).rstrip("\n").split("\t") for _ in range(int(count))]
                    visible = reachable[tier] if eligible == "1" else None
                    results.append(check_term(term, tier, suffix, groups, rules, overlay, excluded,
                                              totals[tier], visible))
                strict, general = results
                dropped = set(map(normalize, strict["actual"].split())) - set(map(normalize, general["actual"].split()))
                if dropped:
                    # A higher-tier exact phrase can replace embedded clues. When both
                    # outputs are exact, an explicitly ranked name can take a display slot.
                    if not strict["exact"] and general["exact"]:
                        reason = "whole_candidate_replaces_embedded"
                    elif strict["exact"] and general["exact"] and term in overlay:
                        reason = "reviewed_name_ranking"
                    else:
                        assert not strict["exact"] and not general["exact"], (term, strict, general)
                        reason = "embedded_groups_change"
                    general["strict_output_replaced"] = sorted(dropped)
                    general["replacement_reason"] = reason
                    totals[2][reason] += 1
                assert not strict["actual"] or general["actual"], term
                report.write(json.dumps({"term": term, "strict": strict, "general": general},
                                        ensure_ascii=False) + "\n")
            assert next(stream, None) is None
        observations.replace(output)
    missing = {tier: sorted(inventory - found) for tier, found in reachable.items()}
    return {
        "core_relations": len(ledger),
        "excluded_core_relations": sum(row["status"] == "excluded" for row in ledger),
        "unique_expressions": len(terms),
        "lua_filter_calls": len(terms) * 2,
        "inventory_size": len(inventory),
        "strict": dict(totals[1]),
        "general": dict(totals[2]),
        "missing_exact_display": {"strict": missing[1], "general": missing[2]},
    }


def check_term(term, tier, suffix, groups, rules, overlay, excluded, totals, reachable):
    entry = overlay.get(term)
    overlay_active = entry is not None and entry["min_tier"] <= tier
    candidates = entry["targets"] if overlay_active else rules.get(term, [])
    eligible_rows = [row for row in candidates if row[1] <= tier]
    eligible = [row[0] for row in eligible_rows]
    whole = []
    allowed_display = set()
    embedded = []
    for phrase, start, finish, level, negation, sequence, raw, display in groups:
        exact = int(start) == 1 and int(finish) == len(term.encode()) + 1
        raw_targets = raw.split()
        display_targets = display.split()
        assert len(raw_targets) == len(display_targets), (term, phrase)
        assert int(level) <= tier, (term, phrase, level)
        assert not any((phrase, normalize(target)) in excluded for target in raw_targets), (term, phrase, raw)
        allowed_display.update(display_targets)
        if negation:
            allowed_display.add(negation)
        if exact:
            assert phrase == term and not whole and raw_targets == eligible, (term, tier, raw_targets, eligible)
            fixed = "" if overlay_active or not eligible_rows[0][3] else eligible[0]
            assert sequence == fixed, (term, tier, sequence, fixed)
            whole = display_targets
            expected = [whole[0]]
            if not sequence and len(whole) > 1 and whole[1] != whole[0]:
                expected.append(whole[1])
            assert suffix.split() == expected, (term, tier, expected, suffix)
            totals["eligible_exact_targets"] += len(eligible)
            totals["exact_targets_beyond_display"] += len(eligible) - len(expected)
            if reachable is not None:
                reachable.update(map(normalize, expected))
        else:
            licensed = [row[0] for row in rules[phrase] if row[1] <= tier and row[2]]
            assert raw_targets == [target for target in licensed if target in raw_targets], (
                term, tier, phrase, raw_targets, licensed)
            embedded.append({"phrase": phrase, "start": int(start), "finish": int(finish), "targets": raw_targets})
    assert bool(whole) == bool(eligible), (term, tier, eligible, groups)
    assert bool(groups) == bool(suffix), (term, tier, suffix, groups)
    assert set(suffix.split()) <= allowed_display, (term, tier, suffix, allowed_display)
    totals["exact" if whole else "embedded_only" if groups else "empty"] += 1
    return {"exact": eligible, "displayable_exact": whole, "embedded": embedded, "actual": suffix,
            "eligible_candidate": reachable is not None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="Gzipped JSONL observations")
    args = parser.parse_args()
    summary = audit(ROOT, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if any(summary["missing_exact_display"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
