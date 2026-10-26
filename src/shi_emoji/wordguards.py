"""Compile noun-boundary guards offline; runtime needs no segmenter."""
import hashlib
import json
from pathlib import Path
import re
from .datafiles import merged_data


def compile_guards(data, lines):
    trie = {}
    for rule in data["rules"]:
        for phrase in rule["phrases"]:
            if len(phrase) < 2:
                continue
            node = trie
            for char in phrase:
                node = node.setdefault(char, {})
            node[None] = True
    guards = set()
    for line in lines:
        word, frequency, tag = line.split()
        if int(frequency) < 3 or not tag.startswith("n"):
            continue
        if not re.fullmatch(r"[\u4e00-\u9fff]{3,8}", word):
            continue
        for start in range(len(word)):
            node = trie
            for end in range(start, len(word)):
                if word[end] not in node:
                    break
                node = node[word[end]]
                if None in node and (start != 0 or end + 1 != len(word)):
                    guards.add(word)
                    break
    return sorted(guards)


def main():
    root = Path(__file__).resolve().parents[2]
    source = root / "data/upstream/jieba-dict.txt"
    data = merged_data(root / "data/phrases.json")
    words = compile_guards(data, source.read_text().splitlines())
    report = {"source": "jieba pinned in data/source_manifest.json", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "policy": "Nouns, frequency >= 3, 3-8 Han characters, containing a proper mapped substring", "words": words}
    (root / "data/word_guards.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Compiled {len(words)} word guards")


if __name__ == "__main__":
    main()
