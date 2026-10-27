# Third-party data notices

Project code and original curated descriptions/rules are MIT. Generated dictionaries also contain adaptations of the datasets below; their original notices remain applicable. Model weights are not distributed.

## Unicode CLDR Chinese annotations

- Source: https://github.com/unicode-org/cldr-json
- Commit: `91c267402229a59e3ef2774544f001bf959e8809`
- License: Unicode-3.0; full notice: [licenses/Unicode-3.0.txt](licenses/Unicode-3.0.txt).
- Usage: Chinese emoji names/keywords, adapted into semantic descriptions, query inventory, and generated mappings.
- The exact source URLs and downloaded SHA-256 values are in `data/source_manifest.json`.
- The lexical baseline additionally uses the same commit's derived Chinese annotations and Unicode Emoji 16.0 `emoji-test.txt` (https://www.unicode.org/Public/emoji/16.0/emoji-test.txt), under the Unicode data license. Their URLs and SHA-256 values are recorded in `data/lexical_phrases.json`. `data/emoji_inventory.json` preserves all fully-qualified entries, including explicitly deferred skin variants.

## jieba dictionary

- Source: https://github.com/fxsjy/jieba
- Commit: `67fa2e36e72f69d9134b8a1037b83fbb070b9775`
- License: MIT; full notice: [licenses/jieba-MIT.txt](licenses/jieba-MIT.txt).
- Usage: Chinese words and frequency/POS signals. Selected 2–6-character noun, verb, adjective, and idiom entries become model queries. No segmentation service runs at typing time.
- Offline noun-boundary guards also adapt this dictionary (frequency >= 3, 3–8 Han characters). Guard words and source SHA-256 are recorded in `data/word_guards.json` and embedded into the Lua runtime dictionary. No jieba library runs at typing time.

## OpenCC traditional-character aliases

- Source: [OpenCC](https://github.com/BYVoid/OpenCC), Python package version `1.4.2`.
- License: Apache-2.0; full notice: [licenses/OpenCC-Apache-2.0.txt](licenses/OpenCC-Apache-2.0.txt).
- Usage: the `s2t.json`, `s2tw.json`, and `s2hk.json` conversion dictionaries generate additional spelling aliases, negators, boundaries, and protected-word forms from this project's existing reviewed mappings. The generated alias file records a source fingerprint and is committed at `data/traditional_aliases.json`.
- OpenCC code and dictionaries are used only when regenerating the source artifact. Neither the library nor its dictionary files are bundled into the typing-time ZIP; the resulting aliases in `data.lua` retain this notice and license.

Redistributors of the generated Lua dictionary must include this file and all three data-license files. Original project data remains MIT; the entire generated dataset should not be labeled solely MIT.

## Build-time model (not bundled)

- Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Revision used: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
- Upstream model card identifies Apache-2.0: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 .
- Used only to propose offline associations, not to encode input while typing. Model weights and Sentence Transformers code are not included in the runtime ZIP. Original project MIT licensing does not relicense upstream software or model weights.
- Source-derived outputs retain applicable Unicode/jieba notices. Model suggestions are not verified factual labels or individually reviewed mappings.

## Runtime and artwork boundaries

Rime, Squirrel, librime-lua and system fonts are user-provided dependencies, not redistributed by this runtime package. Unicode characters are shipped, not Apple/Google or other third-party Emoji artwork. Attribution is not endorsement. The standalone original project examples in `data/emoji.jsonl` are a legacy curated dataset, not an imported external Emoji search corpus.

## Distribution checklist

Keep the root MIT license, this notice, `licenses/Unicode-3.0.txt`, `licenses/jieba-MIT.txt` and `licenses/OpenCC-Apache-2.0.txt` when distributing the generated runtime. The pinned CLDR notice is preserved verbatim rather than replaced with the current Unicode website's copyright year. URLs/commit IDs/SHA-256 records identify the actual source versions. This document records provenance and redistribution notices, not a legal warranty or an audit of upstream data ownership.
