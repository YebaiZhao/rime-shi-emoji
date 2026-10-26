"""Dependency-free, deterministic matching of intent phrases inside Chinese text."""
import argparse
import json
from pathlib import Path
from .datafiles import merged_data


class Matcher:
    def __init__(self, data):
        self.rules = data["rules"]
        self.negators = data["negators"]
        self.boundaries = data["boundaries"]
        self.trie = {}
        self.guard_trie = {}
        for word in data.get("word_guards", []):
            node = self.guard_trie
            for char in word:
                node = node.setdefault(char, {})
            node[None] = True
        seen = set()
        for rule in self.rules:
            if not rule["id"] or not rule["emoji"] or not rule["phrases"]:
                raise ValueError("Each rule needs id, phrases, and emoji")
            for phrase in rule["phrases"]:
                if not phrase or phrase in seen:
                    raise ValueError(f"Empty or duplicate phrase: {phrase!r}")
                seen.add(phrase)
                node = self.trie
                for char in phrase:
                    node = node.setdefault(char, {})
                node[None] = rule

    @classmethod
    def load(cls, path):
        return cls(merged_data(path))

    def search(self, text, top_k=6):
        if top_k < 1:
            raise ValueError("top_k must be positive")
        # Every terminal at every character position is considered. Negation
        # annotates the suggestion; it never removes a lexical match.
        matches, scores = [], {}
        guards = []
        for start in range(len(text)):
            node = self.guard_trie
            for end in range(start, len(text)):
                if text[end] not in node:
                    break
                node = node[text[end]]
                if None in node:
                    guards.append((start, end + 1))
        for position in range(len(text)):
            left = text[:position]
            boundary = max((left.rfind(mark) + len(mark) for mark in self.boundaries if mark in left), default=0)
            prefix = left[boundary:][-4:]
            negated = any(word in prefix for word in self.negators)
            node, end = self.trie, position
            while end < len(text) and text[end] in node:
                node = node[text[end]]
                end += 1
                if None not in node:
                    continue
                rule, phrase = node[None], text[position:end]
                if rule.get("exact_only") and (position != 0 or end != len(text)):
                    continue
                if any(a <= position and end <= b and (a != position or end != b) for a, b in guards):
                    continue
                matches.append({"intent": rule["id"], "phrase": phrase, "start": position,
                                "end": end, "negated": negated})
                for rank, emoji in enumerate(rule["emoji"]):
                    score = len(phrase) * 100 + 20 - rank + rule.get("priority", 0)
                    previous = scores.get(emoji)
                    if (previous is None or score > previous["score"]
                            or (score == previous["score"] and previous["negated"] and not negated)):
                        scores[emoji] = {"emoji": emoji, "score": score, "phrase": phrase,
                                         "intent": rule["id"], "negated": negated}
        candidates = sorted(scores.values(), key=lambda row: (-row["score"], row["emoji"]))[:top_k]
        return {"query": text, "matches": matches, "candidates": candidates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("--phrases", type=Path, default=Path("data/phrases.json"))
    parser.add_argument("--top-k", type=int, default=6)
    args = parser.parse_args()
    data = merged_data(args.phrases)
    result = Matcher(data).search(args.text, args.top_k)
    phrases = {hit["phrase"] for hit in result["matches"]} | {args.text}
    result["mapping_sources"] = {phrase: data.get("mapping_audit", {}).get(phrase, []) for phrase in sorted(phrases)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
