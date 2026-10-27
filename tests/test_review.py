import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from shi_emoji.datafiles import merged_data


class ReviewBoundaryTests(unittest.TestCase):
    def test_unsigned_or_changed_generated_data_is_not_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "phrases.json").write_text(json.dumps({"rules": []}))
            (root / "short_term_policy.json").write_text(json.dumps({
                "standalone_single": {}, "contextual_single": {}}))
            generated = root / "model_phrases.json"
            generated.write_text(json.dumps({"rules": [], "attribution": "test"}))
            with self.assertRaisesRegex(ValueError, "need"):
                merged_data(root / "phrases.json")
            (root / "model_review.json").write_text(json.dumps({
                "artifact_sha256": hashlib.sha256(generated.read_bytes()).hexdigest()}))
            self.assertEqual(merged_data(root / "phrases.json")["rules"], [])
            generated.write_text(json.dumps({"rules": [], "attribution": "changed"}))
            with self.assertRaisesRegex(ValueError, "changed"):
                merged_data(root / "phrases.json")
