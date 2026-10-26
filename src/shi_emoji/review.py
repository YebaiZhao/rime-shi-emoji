"""Record an explicit maintainer review against exact generated artifact bytes."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    record = {"reviewer": args.reviewer, "date": date.today().isoformat(),
              "scope": "Intermediate semantic scan plus final alias/cluster samples, thresholds and corrections; not every mapping individually reviewed",
              "artifact_sha256": digest("data/model_phrases.json"),
              "predictions_sha256": digest("data/model_predictions.json"),
              "policy_sha256": digest("data/review_policy.json"),
              "summary": str(args.summary), "summary_sha256": digest(args.summary)}
    Path("data/model_review.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print("Recorded review for generated artifact", record["artifact_sha256"])


if __name__ == "__main__":
    main()
