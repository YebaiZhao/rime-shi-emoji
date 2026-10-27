# Reverse coverage baseline

Latest policy: see [per-phrase resolution](mapping-resolution.md) and [short-term evaluation](evaluation.md). The current generated baseline is 0 zero-term entries, 444 below three terms, 652 below four, and 0 without a primary term. The earlier per-phrase policy-change record is `data/merge_policy_baseline.json`; these are not comparable accuracy measurements.

This development milestone is not installed into the active input method.

## Reproduce

```sh
PYTHONPATH=src python -m shi_emoji.coverage --fetch --check
PYTHONPATH=src python -m shi_emoji.export
PYTHONPATH=src python -m unittest discover -s tests -v
```

Pinned Unicode Emoji 16.0 defines the denominator, not the previous model catalog. CLDR ordinary and derived Chinese annotations use the existing fixed commit. Inputs are cached under ignored `data/upstream/`; generated inventory, lexical entries, source SHA-256s and coverage report are committed deliverables.

## Policy

- Inventory all 3,781 fully-qualified entries. The baseline targets 1,906 entries without skin modifiers. The remaining 1,875 variants remain explicitly inventoried but not separately expanded.
- Use official Chinese names and keywords occurring on at most two base emoji. Exclude broad shared keywords to avoid mapping arbitrary words to dozens of emoji.
- Country flags additionally accept their CLDR region name, region name + 国旗 and region name + 旗帜. These are deterministic lexical aliases, not model output.
- Human-reviewed associations live separately in `data/lexical_aliases.json`; 三文鱼→🍣 and 飞人→🕴️ are associations, not claims of synonymy.
- Reviewed standalone single-character and non-Chinese lexical entries only match the complete candidate; the small contextual-single list requires a longer candidate. Weak two-character terms also require longer context.
- Per-phrase source resolution gives curated rules precedence, then reviewed lexical terms, then model terms. Explicit atomic suffixes retain their phrase scope.

## Audit boundaries

`data/coverage_report.json` lists every emoji, all entry terms and primary entry terms. All 1,906 base entries have at least one mapped term. This does NOT imply every emoji appears in the final enhanced suffix: the composer selects at most three concepts and one primary emoji per concept (up to two for a single concept). Primary-entry gaps are tracked separately.

Build-time Traditional spelling aliases are deliberately excluded from these semantic-coverage counts: a second script form of the same term is not a new meaning. They are included in runtime matching and tested separately.

The latest exact counts are in `data/coverage_report.json`; `data/coverage_budget.json` sets non-regression limits for the four summary metrics. Both `--check` and the offline tests enforce them. These are lexical mapping counts, not reachability after word guards or final composition. Do not satisfy these by inventing unrelated words. Next work: supervised alias expansion for the audited gaps, disambiguation and final-render reachability tests across the whole inventory. The old model catalog remains unchanged for reproducibility; future model builds must explicitly adopt the new inventory rather than silently invalidating existing prediction/review hashes.
