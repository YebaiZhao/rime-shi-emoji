"""Batch model predictions with auditable gates and separate human overrides."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import random
import time

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def gate(query, candidates, policy, curated):
    if query in curated:
        return "curated"
    if query in policy["reject_queries"] or query in policy.get("review_rejects", []):
        return "review_rejected"
    # Avoid a long generated phrase swallowing a deliberate shorter mapping.
    if any(phrase in query for phrase in curated):
        return "contains_curated"
    if candidates[0].get("matched_text") == query:
        return "accepted_alias"
    if "matched_text" in candidates[0] and len(candidates[0]["matched_text"]) < 2:
        return "short_alias"
    if candidates[0].get("context_rank", 1) > 10 or candidates[0].get("context_score", 1) < 0.5:
        return "weak_context"
    if candidates[0]["score"] < policy["min_score"]:
        return "low_score"
    if (candidates[0].get("matched_text") is not None
            and candidates[0]["matched_text"] == candidates[1].get("matched_text")
            and candidates[1].get("context_rank", 999) <= 10
            and candidates[1].get("context_score", 0) >= 0.5):
        return "accepted_cluster"
    if candidates[0]["score"] - candidates[1]["score"] < policy["min_margin"]:
        return "ambiguous"
    return "accepted"


def materialize(predictions, policy):
    rules = []
    for row in predictions:
        query = row["query"]
        if query in policy["overrides"]:
            emojis = policy["overrides"][query]
            origin = "human-reviewed-override"
        elif row["status"] in {"accepted", "accepted_alias", "accepted_cluster"}:
            first = row["candidates"][0]["score"]
            emojis = [item["emoji"] for item in row["candidates"][:3]
                      if item["score"] >= policy["alternative_min_score"]
                      and first - item["score"] <= policy["alternative_max_drop"]]
            origin = "existing-alias" if row["status"] == "accepted_alias" else "model-thresholded"
        else:
            continue
        if not emojis:
            raise ValueError(f"Empty approved mapping: {query}")
        rules.append({"id": "model:" + query, "phrases": [query], "emoji": emojis,
                      "priority": -1000, "origin": origin,
                      "model_score_basis_points": round(row["candidates"][0]["score"] * 10000)})
    return rules


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", action="store_true", help="Reapply review policy to saved predictions, without inference")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--revision", default=REVISION)
    args = parser.parse_args()
    policy = json.loads(Path("data/review_policy.json").read_text())
    curated_data = json.loads(Path("data/phrases.json").read_text())
    curated = {phrase for rule in curated_data["rules"] for phrase in rule["phrases"]}
    queries = json.loads(Path("data/model_queries.json").read_text())
    catalog = json.loads(Path("data/model_catalog.json").read_text())
    if args.reuse:
        report = json.loads(Path("data/model_predictions.json").read_text())
        if report["queries_sha256"] != hashlib.sha256(Path("data/model_queries.json").read_bytes()).hexdigest():
            raise ValueError("Query inventory changed; rerun inference without --reuse")
        if report["catalog_sha256"] != hashlib.sha256(Path("data/model_catalog.json").read_bytes()).hexdigest():
            raise ValueError("Emoji descriptions changed; rerun inference without --reuse")
        predictions = report["predictions"]
    else:
        import numpy as np
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(4)
        started = time.perf_counter()
        model = SentenceTransformer(args.model, revision=args.revision, local_files_only=True, device="cpu")
        # Encode names and usage phrases separately rather than long keyword
        # concatenations. Mean centering reduces universal-neighbor hubs.
        views = []
        for i, row in enumerate(catalog):
            phrases = [text for text in dict.fromkeys(row["description"].split("，")) if len(text.strip()) >= 2]
            if not phrases:
                phrases = [row["description"].replace("，", "")]
            views.extend((text, i) for text in phrases)
        unique = list(dict.fromkeys(text for text, _ in views))
        encoded = model.encode(unique, batch_size=64, normalize_embeddings=True, show_progress_bar=True)
        mean = encoded.mean(axis=0)
        encoded = encoded - mean
        encoded /= np.linalg.norm(encoded, axis=1, keepdims=True)
        lookup = {text: i for i, text in enumerate(unique)}
        descriptions = encoded[[lookup[text] for text, _ in views]]
        contexts = model.encode([row["description"] for row in catalog], batch_size=64,
                                normalize_embeddings=True, show_progress_bar=True) - mean
        contexts /= np.linalg.norm(contexts, axis=1, keepdims=True)
        owners = np.array([i for _, i in views])
        view_indices = [np.where(owners == i)[0] for i in range(len(catalog))]
        vectors = model.encode([row["query"] for row in queries], batch_size=64,
                               normalize_embeddings=True, show_progress_bar=True)
        vectors = vectors - mean
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        predictions = []
        for offset in range(0, len(queries), 256):
            scores = vectors[offset:offset + 256] @ descriptions.T
            context_scores = vectors[offset:offset + 256] @ contexts.T
            for row, view_scores, context_sim in zip(queries[offset:offset + 256], scores, context_scores):
                similarities = np.full(len(catalog), -np.inf)
                np.maximum.at(similarities, owners, view_scores)
                indices = np.lexsort((-context_sim, -similarities))[:5]
                predictions.append({"query": row["query"], "sources": row["sources"],
                    "candidates": [{"emoji": catalog[int(i)]["emoji"], "score": round(float(similarities[i]), 6),
                                    "matched_text": views[int(view_indices[i][np.argmax(view_scores[view_indices[i]])])][0],
                                    "context_score": round(float(context_sim[i]), 6),
                                    "context_rank": int(np.count_nonzero(context_sim > context_sim[i])) + 1,
                                    "description": catalog[int(i)]["description"]} for i in indices]})
        report = {"model": args.model, "model_revision": args.revision,
                  "encoding_strategy": "separate name/keyword/usage views, mean-centered normalized embeddings, max per emoji",
                  "sentence_transformers": version("sentence-transformers"),
                  "torch": version("torch"), "emoji_count": len(catalog), "query_count": len(queries),
                  "inference_seconds": time.perf_counter() - started, "predictions": predictions,
                  "catalog_sha256": hashlib.sha256(Path("data/model_catalog.json").read_bytes()).hexdigest(),
                  "queries_sha256": hashlib.sha256(Path("data/model_queries.json").read_bytes()).hexdigest()}
    counts = {}
    for row in predictions:
        row["status"] = gate(row["query"], row["candidates"], policy, curated)
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    report["gate_counts"] = counts
    report["policy_sha256"] = hashlib.sha256(Path("data/review_policy.json").read_bytes()).hexdigest()
    Path("data/model_predictions.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    rules = materialize(predictions, policy)
    artifact = {"model": report["model"], "model_revision": report["model_revision"],
                "attribution": "Includes Unicode CLDR data (Unicode-3.0) and jieba vocabulary (MIT); see THIRD_PARTY_NOTICES.md",
                "review_status": "Automated gates plus sampled human/assistant review; not individually reviewed",
                "rules": rules}
    Path("data/model_phrases.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    accepted = [row for row in predictions if row["status"] in {"accepted", "accepted_alias", "accepted_cluster"}]
    semantic = [row for row in accepted if row["status"] in {"accepted", "accepted_cluster"}]
    aliases = [row for row in accepted if row["status"] == "accepted_alias"]
    sample = random.Random(20261026).sample(semantic, min(100, len(semantic)))
    sample += random.Random(20261027).sample(aliases, min(50, len(aliases)))
    sample += sorted(accepted, key=lambda row: row["candidates"][0]["score"])[:30]
    sample += [row for row in predictions if row["query"] in policy["overrides"]]
    lines = ["# Model review sample", "", "| Query | Status | Model top 3 (similarity) |", "| --- | --- | --- |"]
    for row in sample:
        values = " · ".join(f"{c['emoji']} {c['score']:.3f}" for c in row["candidates"][:3])
        lines.append(f"| {row['query']} | {row['status']} | {values} |")
    Path("docs/model-review-sample.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"gates": counts, "generated_rules": len(rules), "inference_seconds": report["inference_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
