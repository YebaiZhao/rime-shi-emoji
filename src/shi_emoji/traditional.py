"""Generate reviewed-source Traditional aliases; OpenCC runs only at build time."""
from collections import defaultdict
from importlib.metadata import version
import json
from pathlib import Path

from .datafiles import merged_data, traditional_source_sha256


OPENCC_VERSION = "1.4.2"
CONFIGS = ("s2t.json", "s2tw.json", "s2hk.json")


def signature(rule):
    return tuple(rule["emoji"]), rule.get("suffix"), rule.get("priority"), rule.get("exact_only"), rule.get("min_context_len")


def generate(data, converters):
    originals = {rule["phrases"][0]: rule for rule in data["rules"]}
    proposed = defaultdict(set)
    for phrase in sorted(originals):
        for convert in converters:
            alias = convert(phrase)
            if alias != phrase and alias not in originals:
                proposed[alias].add(phrase)
    aliases = {}
    for alias, sources in sorted(proposed.items()):
        if len({signature(originals[source]) for source in sources}) != 1:
            raise ValueError(f"Traditional alias has conflicting meanings: {alias} <- {sorted(sources)}")
        aliases[alias] = sorted(sources)[0]
    result = {"version": 1, "opencc_version": OPENCC_VERSION, "configs": list(CONFIGS),
              "source_sha256": traditional_source_sha256(data), "aliases": aliases}
    for key in ("word_guards", "negators", "boundaries"):
        original = set(data[key])
        result[key] = sorted({convert(item) for item in original for convert in converters} - original)
    return result


def main():
    if version("opencc") != OPENCC_VERSION:
        raise RuntimeError(f"Install build-time OpenCC=={OPENCC_VERSION}")
    import opencc
    data = merged_data("data/phrases.json", include_traditional=False)
    converters = [opencc.OpenCC(config).convert for config in CONFIGS]
    artifact = generate(data, converters)
    output = Path("data/traditional_aliases.json")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Generated {len(artifact['aliases'])} Traditional aliases and "
          f"{len(artifact['word_guards'])} guard aliases in {output}")


if __name__ == "__main__":
    main()
