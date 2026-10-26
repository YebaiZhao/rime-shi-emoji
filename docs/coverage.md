# Reverse coverage baseline

Latest policy: see [per-phrase resolution](mapping-resolution.md). Historical counts below describe the earlier union policy. Current resolved baseline: 0 zero-term entries, 405 below three terms, 601 below four, 12 without a primary term. The policy-change record is `data/merge_policy_baseline.json`; these are not comparable accuracy measurements.

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
- Single-character and non-Chinese lexical entries only match the complete candidate. Normal Chinese multi-character terms can match inside sentences.
- Existing semantic order and explicit atomic suffixes take precedence; lexical alternatives append without removing existing mappings.

## Audit boundaries

`data/coverage_report.json` lists every emoji, all entry terms and primary entry terms. All 1,906 base entries have at least one mapped term. This does NOT imply every emoji appears in the final enhanced suffix: the composer selects at most three concepts and one primary emoji per concept (up to two for a single concept). Primary-entry gaps are tracked separately.

There are still 362 base entries with fewer than three terms, 551 with fewer than four, and 11 with no primary entry. `data/coverage_budget.json` sets non-regression limits for these four metrics; both `--check` and the offline tests enforce them. These are lexical mapping counts, not reachability after word guards or final composition. Do not satisfy these by inventing unrelated words. Next work: supervised alias expansion for these exact gaps, disambiguation and final-render reachability tests across the whole inventory. The old model catalog remains unchanged for reproducibility; future model builds must explicitly adopt the new inventory rather than silently invalidating existing prediction/review hashes.
