"""Prepare pinned, attributed public vocabulary for model-assisted dictionary builds."""
import hashlib
import json
from pathlib import Path
import re
import urllib.request

CLDR = "91c267402229a59e3ef2774544f001bf959e8809"
JIEBA = "67fa2e36e72f69d9134b8a1037b83fbb070b9775"
SOURCES = {
    "data/upstream/cldr-zh.json": f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR}/cldr-json/cldr-annotations-full/annotations/zh/annotations.json",
    "licenses/Unicode-3.0.txt": f"https://raw.githubusercontent.com/unicode-org/cldr-json/{CLDR}/LICENSE",
    "data/upstream/jieba-dict.txt": f"https://raw.githubusercontent.com/fxsjy/jieba/{JIEBA}/jieba/dict.txt",
    "licenses/jieba-MIT.txt": f"https://raw.githubusercontent.com/fxsjy/jieba/{JIEBA}/LICENSE",
}


def usable_emoji(text):
    return (any(0x1F000 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF for c in text)
            and not any(0x1F1E6 <= ord(c) <= 0x1F1FF or 0x1F3FB <= ord(c) <= 0x1F3FF for c in text)
            and "\u200d" not in text)


def main():
    manifest = {}
    for filename, url in SOURCES.items():
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            print("Downloading", url, flush=True)
            path.write_bytes(urllib.request.urlopen(url, timeout=60).read())
        manifest[filename] = {"url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    annotations = json.loads(Path("data/upstream/cldr-zh.json").read_text())["annotations"]["annotations"]
    seeds = json.loads(Path("data/phrases.json").read_text())
    catalog, terms = {}, {}
    for emoji, entry in annotations.items():
        if not usable_emoji(emoji):
            continue
        description = "，".join(dict.fromkeys(entry.get("tts", []) + entry.get("default", [])))
        key = emoji.replace("\ufe0f", "")
        catalog[key] = {"emoji": emoji, "description": description, "source": "unicode-cldr"}
        for word in entry.get("tts", []) + entry.get("default", []):
            if re.fullmatch(r"[\u4e00-\u9fff]{2,6}", word):
                terms.setdefault(word, set()).add("unicode-cldr")
    for rule in seeds["rules"]:
        emoji = rule["emoji"][0]
        key = emoji.replace("\ufe0f", "")
        extra = "，".join(rule["phrases"])
        if key in catalog:
            catalog[key]["description"] += "，" + extra
            catalog[key]["emoji"] = emoji
        else:
            catalog[key] = {"emoji": emoji, "description": extra, "source": "project-curated"}
    frequencies = []
    for line in Path("data/upstream/jieba-dict.txt").read_text().splitlines():
        word, frequency, tag = line.split()
        if re.fullmatch(r"[\u4e00-\u9fff]{2,6}", word) and tag in {"n", "v", "a", "vn", "an", "i"}:
            frequencies.append((int(frequency), word))
    for _, word in sorted(frequencies, reverse=True)[:16000]:
        terms.setdefault(word, set()).add("jieba")
    for rule in seeds["rules"]:
        for word in rule["phrases"]:
            terms.setdefault(word, set()).add("project-curated")
    for word in json.loads(Path("data/everyday_queries.json").read_text()):
        if not re.fullmatch(r"[\u4e00-\u9fff]{2,6}", word):
            raise ValueError(f"Invalid everyday query: {word}")
        terms.setdefault(word, set()).add("project-everyday-query")
    catalog_rows = list(catalog.values())
    query_rows = [{"query": word, "sources": sorted(sources)} for word, sources in sorted(terms.items())]
    Path("data/model_catalog.json").write_text(json.dumps(catalog_rows, ensure_ascii=False, indent=2) + "\n")
    Path("data/model_queries.json").write_text(json.dumps(query_rows, ensure_ascii=False, indent=2) + "\n")
    Path("data/source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(catalog_rows)} emoji descriptions and {len(query_rows)} queries")


if __name__ == "__main__":
    main()
