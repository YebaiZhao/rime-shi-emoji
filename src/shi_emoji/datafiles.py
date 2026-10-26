"""Load curated mappings and only explicitly reviewed generated artifacts."""
import hashlib
from copy import deepcopy
import json
from pathlib import Path


def resolve_layers(layers):
    """Resolve per phrase, without mutating or sharing source rule objects."""
    offers = {}
    scoped = {}
    for _, _, rules in layers:
        for rule in rules:
            if rule.get("suffix"):
                scoped.setdefault(rule["suffix"], set()).update(rule["phrases"])
    for source, rank, rules in layers:
        for rule in rules:
            for phrase in rule["phrases"]:
                item = deepcopy(rule)
                item["phrases"] = [phrase]
                item["emoji"] = [e for e in item["emoji"]
                                 if source == "curated" or e not in scoped or phrase in scoped[e]]
                effective_rank = 50 if source == "lexical" and rule.get("kind") == "keyword" else rank
                offers.setdefault(phrase, []).append({"source": source, "rank": effective_rank,
                    "kind": rule.get("kind", "expression" if source == "curated" else "association"),
                    "original_emoji": list(rule["emoji"]), "rule": item})
    result, audit = [], {}
    for phrase, candidates in offers.items():
        eligible = [c for c in candidates if c["rule"]["emoji"]]
        winner = max(eligible, key=lambda c: c["rank"]) if eligible else None
        audit[phrase] = [{"source": c["source"], "kind": c["kind"],
                         "origin": c["rule"].get("origin", c["kind"]),
                         "original_emoji": c["original_emoji"], "eligible_emoji": c["rule"]["emoji"],
                         "selected": c is winner} for c in candidates]
        if winner:
            output = deepcopy(winner["rule"])
            output["mapping_source"] = winner["source"]
            output["kind"] = winner["kind"]
            result.append(output)
    return result, audit


def merged_data(path, include_generated=True):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    generated_path = path.parent / "model_phrases.json"
    if not include_generated or not generated_path.exists():
        return data
    review_path = path.parent / "model_review.json"
    if not review_path.exists():
        raise ValueError("Generated mappings need data/model_review.json before export")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    actual = hashlib.sha256(generated_path.read_bytes()).hexdigest()
    if review["artifact_sha256"] != actual:
        raise ValueError("Generated mappings changed after review; inspect and update review record")
    generated = json.loads(generated_path.read_text(encoding="utf-8"))
    seen = {phrase for rule in data["rules"] for phrase in rule["phrases"]}
    for rule in generated["rules"]:
        if any(phrase in seen for phrase in rule["phrases"]):
            raise ValueError("Generated mappings conflict with curated mappings")
        seen.update(rule["phrases"])
    data["attribution"] = generated["attribution"]
    layers = [("curated", 300, data["rules"]),
              ("model", 100, generated["rules"])]
    lexical_path = path.parent / "lexical_phrases.json"
    if lexical_path.exists():
        layers.append(("lexical", 200, json.loads(lexical_path.read_text(encoding="utf-8"))["rules"]))
    data["rules"], data["mapping_audit"] = resolve_layers(layers)
    guards_path = path.parent / "word_guards.json"
    if guards_path.exists():
        generated_guards = json.loads(guards_path.read_text(encoding="utf-8"))["words"]
        data["word_guards"] = sorted(set(data.get("word_guards", [])) | set(generated_guards))
    return data
