"""Build pinned Unicode inventory, conservative lexical entries and reverse audit."""
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from .sources import CLDR

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    "emoji-test-16.0.txt": "https://www.unicode.org/Public/emoji/16.0/emoji-test.txt",
    "cldr-zh.json": f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR}/cldr-json/cldr-annotations-full/annotations/zh/annotations.json",
    "cldr-derived-zh.json": f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR}/cldr-json/cldr-annotations-derived-full/annotationsDerived/zh/annotations.json",
}


def normalize(text):
    return text.replace("\ufe0f", "")


def inventory(root=ROOT):
    annotations = {}
    for filename in ("cldr-zh.json", "cldr-derived-zh.json"):
        doc = json.loads((root / "data/upstream" / filename).read_text())
        container = doc.get("annotations", doc.get("annotationsDerived"))
        annotations.update({normalize(k): v for k, v in container["annotations"].items()})
    rows, group, subgroup = [], "", ""
    for line in (root / "data/upstream/emoji-test-16.0.txt").read_text().splitlines():
        if line.startswith("# group: "):
            group = line[9:]
        elif line.startswith("# subgroup: "):
            subgroup = line[12:]
        elif "; fully-qualified" in line:
            codes, tail = line.split(";", 1)
            emoji = "".join(chr(int(c, 16)) for c in codes.split())
            entry = annotations.get(normalize(emoji), {})
            rows.append({"emoji": emoji, "name_en": re.split(r" E[0-9.]+ ", tail, maxsplit=1)[1],
                         "group": group, "subgroup": subgroup,
                         "skin_variant": any(0x1F3FB <= ord(c) <= 0x1F3FF for c in emoji),
                         "names": entry.get("tts", []), "keywords": entry.get("default", [])})
    return rows


def build(root=ROOT):
    rows = inventory(root)
    frequencies = Counter(w for r in rows if not r["skin_variant"] for w in set(r["keywords"]))
    aliases = defaultdict(list)
    official_names = {name for row in rows if not row["skin_variant"] for name in row["names"]}
    for row in rows:
        if row["skin_variant"]:
            continue
        terms = row["names"] + [w for w in row["keywords"] if frequencies[w] <= 2]
        if row["subgroup"] == "country-flag":
            for name in row["names"]:
                country = re.sub(r"^旗[:：]\s*", "", name)
                terms += [country, country + "国旗", country + "旗帜"]
                official_names.update([country, country + "国旗", country + "旗帜"])
        for term in dict.fromkeys(terms):
            if term and row["emoji"] not in aliases[term]:
                aliases[term].append(row["emoji"])
    # A country name must lead with its flag, even if a cultural keyword for
    # another emoji appeared earlier in the Unicode inventory.
    for row in rows:
        if row["skin_variant"] or row["subgroup"] != "country-flag":
            continue
        for name in row["names"]:
            country = re.sub(r"^旗[:：]\s*", "", name)
            aliases[country] = [row["emoji"]] + [emoji for emoji in aliases[country]
                                                  if emoji != row["emoji"]]
    valid = {normalize(r["emoji"]) for r in rows}
    literal_aliases = json.loads((root / "data/literal_aliases.json").read_text())
    association_aliases = json.loads((root / "data/lexical_aliases.json").read_text())
    for term, emojis in association_aliases.items():
        for emoji in emojis:
            if normalize(emoji) not in valid:
                raise ValueError(f"Not in pinned inventory: {emoji}")
            if emoji not in aliases[term]:
                aliases[term].append(emoji)
    for term, emojis in literal_aliases.items():
        if not emojis or any(normalize(e) not in valid for e in emojis):
            raise ValueError(f"Invalid literal alias: {term}")
        aliases[term] = emojis
    rules = [{"id": "lexical:" + term, "phrases": [term], "emoji": emojis,
              "priority": -500, "kind": "literal" if term in literal_aliases else ("name" if term in official_names else ("association" if term in association_aliases else "keyword")),
              "exact_only": len(term) == 1 or not re.search(r"[\u4e00-\u9fff]", term)}
             for term, emojis in sorted(aliases.items())]
    sources = {name: {"url": url, "sha256": hashlib.sha256((root / "data/upstream" / name).read_bytes()).hexdigest()}
               for name, url in INPUTS.items()}
    artifact = {"sources": sources, "policy": "CLDR names and keywords shared by at most two base emoji; skin variants inventoried, not expanded", "rules": rules}
    for filename, value in (("emoji_inventory.json", rows), ("lexical_phrases.json", artifact)):
        (root / "data" / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return rows


def audit(rows, data):
    terms, primary = defaultdict(set), defaultdict(set)
    for rule in data["rules"]:
        for emoji in rule["emoji"]:
            terms[normalize(emoji)].update(rule["phrases"])
        primary[normalize(rule["emoji"][0])].update(rule["phrases"])
    entries = [{**r, "terms": sorted(terms[normalize(r["emoji"])]),
                "primary_terms": sorted(primary[normalize(r["emoji"])])} for r in rows]
    base = [r for r in entries if not r["skin_variant"]]
    return {"summary": {"unicode_version": "16.0", "inventory": len(entries), "base_emoji": len(base),
                        "skin_variants_deferred": len(entries) - len(base),
                        "zero_terms": sum(not r["terms"] for r in base),
                        "under_three": sum(len(r["terms"]) < 3 for r in base),
                        "under_four": sum(len(r["terms"]) < 4 for r in base),
                        "zero_primary": sum(not r["primary_terms"] for r in base)}, "entries": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--fetch", action="store_true", help="Download missing pinned inputs")
    args = parser.parse_args()
    if args.fetch:
        for filename, url in INPUTS.items():
            path = ROOT / "data/upstream" / filename
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(urllib.request.urlopen(url, timeout=40).read())
    rows = build()
    from .datafiles import merged_data
    # Script variants are spelling aliases, not additional semantic coverage.
    report = audit(rows, merged_data(ROOT / "data/phrases.json", include_traditional=False))
    (ROOT / "data/coverage_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    limits = json.loads((ROOT / "data/coverage_budget.json").read_text())
    regressions = {key: report["summary"][key] for key, maximum in limits.items()
                   if report["summary"][key] > maximum}
    if args.check and regressions:
        raise SystemExit(f"Coverage regression: {regressions}; inspect data/coverage_report.json")


if __name__ == "__main__":
    main()
