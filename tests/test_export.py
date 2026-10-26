import json
from pathlib import Path
import unittest
from shi_emoji.export import runtime_source
from shi_emoji.datafiles import merged_data


class ExportTests(unittest.TestCase):
    def test_committed_runtime_data_matches_source(self):
        data = merged_data("data/phrases.json")
        expected = runtime_source(data)
        self.assertEqual(Path("rime/lua/shi_emoji/data.lua").read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
