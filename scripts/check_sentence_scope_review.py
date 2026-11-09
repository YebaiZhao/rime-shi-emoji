"""Verify all sentence-scope batches against the frozen source ledger."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "data"
REVIEW = ROOT / "sentence_scope_review"
DECISION_BY_FAMILY = {
    "word": "whole_token",
    "utterance": "whole_candidate_only",
    "sense": "requires_disambiguation",
    "operator": "requires_disambiguation",
}
EXPECTED_POSITIVE = {
    "whole_token": "eligible_after_verified_token_and_assertion",
    "whole_candidate_only": "exact_candidate_only",
    "requires_disambiguation": "eligible_only_if_required_features_verified",
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def verify_batch(path, queue, first, digest, norm, signatures):
    summary = json.loads(path.with_name(path.stem + "-summary.json").read_text())
    assert summary["source_sha256"] == digest
    assert summary["source_queue_size"] == len(queue)
    assert summary["first_queue_index"] == first
    proposals = read_jsonl(path)
    last = summary["last_queue_index"]
    assert 1 <= len(proposals) == last - first + 1 <= 800
    assert summary["remaining"] == len(queue) - last
    assert summary["runtime_validation"] == "not_run"
    assert summary["sentence_authorized"] == 0
    assert Counter(row["decision"] for row in proposals) == summary["decisions"]
    assert Counter(row["context_family"] for row in proposals) == summary["context_families"]

    source_batch = queue[first - 1:last]
    assert len(source_batch) == len(proposals)
    by_id = {}
    for index, (proposal, original) in enumerate(zip(proposals, source_batch), first):
        assert proposal["queue_index"] == index
        for key in ("id", "core_index", "expression", "target", "min_tier"):
            assert proposal[key] == original[key], (index, key)
        assert original["status"] == "approved" and proposal["source_scope"] == "C"
        assert proposal["context_basis"] == original["rationale"]
        assert proposal["reason"].strip() and proposal["condition_spec"]
        assert proposal["sentence_authorized"] is False
        assert proposal["runtime_validation"] == "not_run"
        normalized = (norm.get(original["expression"], original["expression"]),
                      original["target"].replace("\ufe0f", ""))
        assert tuple(proposal["normalization_key"]) == normalized
        family = proposal["context_family"]
        decision = proposal["decision"]
        assert DECISION_BY_FAMILY[family] == decision
        conditions = tuple(proposal["condition_spec"])
        domain = proposal["condition_values"].get("operation_or_domain")
        signature = (decision, family, conditions, domain)
        assert signatures.setdefault(normalized, signature) == signature, normalized
        if decision == "whole_candidate_only":
            assert conditions == ("exact_candidate",)
        else:
            assert "verified_token_boundary" in conditions
        if decision == "requires_disambiguation":
            assert proposal["condition_values"]
            assert proposal["condition_evaluation"] == "requires_verified_features"
        if family == "operator":
            assert domain
        by_id[proposal["id"]] = proposal

    assert len(by_id) == len(proposals)
    cases = json.loads(path.with_name(path.stem + "-examples.json").read_text())
    assert cases["kind"] == "design_examples_not_runtime_fixtures"
    for case in cases["examples"]:
        row = by_id[case["id"]]
        for key in ("queue_index", "expression", "target", "decision"):
            assert case[key] == row[key], (case["id"], key)
        assert case["expression"] in case["positive"]
        assert case["expression"] in case["negative"]
        assert case["expected_positive"] == EXPECTED_POSITIVE[row["decision"]]
        assert case["expected_negative"] == "no_sentence_trigger"
    return proposals, len(cases["examples"])


def main():
    source = ROOT / "relation_reviews.jsonl"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    queue = [row for row in read_jsonl(source) if row["scope_review"]["code"] == "C"]
    norm = json.loads((ROOT / "relation_review/expression_normalization.json").read_text())
    signatures = {}
    reviewed = []
    example_count = 0
    for number, path in enumerate(sorted(REVIEW.glob("batch-*.jsonl")), 1):
        assert path.stem == f"batch-{number:03}"
        batch, count = verify_batch(path, queue, len(reviewed) + 1, digest, norm, signatures)
        reviewed.extend(batch)
        example_count += count
    assert len({row["id"] for row in reviewed}) == len(reviewed) == len(queue)
    assert json.loads((REVIEW / "progress.json").read_text()) == {
        "source_sha256": digest,
        "source_queue_size": len(queue),
        "reviewed": len(reviewed),
        "remaining": 0,
        "next_queue_index": None,
        "decisions": dict(Counter(row["decision"] for row in reviewed)),
        "context_families": dict(Counter(row["context_family"] for row in reviewed)),
        "runtime_validation": "not_run",
        "sentence_authorized": 0,
    }
    print(f"Verified {len(reviewed)} proposals against {len(queue)} C relations, "
          f"{example_count} design examples")


if __name__ == "__main__":
    main()
