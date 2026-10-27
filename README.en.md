# Shi Emoji · 诗Emoji

**Keep your Chinese text. Add a little expression.**

A lightweight Rime / Squirrel plugin that previews emoji only beside the highlighted Chinese candidate. Press Option+Return to commit **text + emoji**. No runtime AI model, network request, or background service.

[中文](README.md) · [Install](INSTALL.md) · [Architecture](docs/architecture.md) · [Contribute](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

```text
我不想去海边 → 我不想去海边 🙅 🏖️
牛逼         → 牛逼 🐂🍺
德国         → 德国 🇩🇪
三文鱼       → 三文鱼 🍣
开发         → 开发 🧑‍💻
```

These are checked examples, not a promise to understand arbitrary Chinese. Matching uses finite phrase dictionaries, local heuristics and offline-reviewed associations.

## Why try it?

- Original candidate order stays intact. Space commits plain text and Tab retains the host schema's behavior; highlight a candidate and press Option+Return to commit its previewed emoji.
- An [experimental numbered candidate slot](docs/experimental-candidate-slot.md) is available as an opt-in: its number key commits emoji only. It sets a seven-item page, so an ordinary seventh candidate may still appear when there is no emoji match, and Wanxiang's `7` key no longer serves its original tone behavior. The default installation does not enable it.
- Finds several concepts inside a sentence, rather than requiring an exact whole-sentence entry.
- Runs locally with Lua and static data. The plugin does not collect typing telemetry; host IME logging is separate.
- The native menu keeps only the main switch. Skin tone, gender and optional edgy associations (重口联想) are static schema settings; one archive includes everything, with edgy associations off by default.
- Auditable data: official names, curated literal meanings and associations, and model suggestions are resolved separately.

## Install and use

**v0.1.0-alpha.1** is a prerelease candidate, primarily tested with macOS Squirrel and Simplified Chinese candidates. Installation into Luna Pinyin Simplified has also been checked in an isolated profile. Traditional-character vocabulary coverage is limited; other frontends are not yet verified.

When a release is available, download `rime-shi-emoji-runtime.zip` from this repository's Releases. Until then, use **Code → Download ZIP** on GitHub and copy from `rime/lua/shi_emoji` instead of `lua/shi_emoji`; the YAML examples are in `rime/`. End users do not need Python.

Copy `lua/shi_emoji` into the Rime user directory; merge the two bundled YAML examples into your Chinese schema custom file and `default.custom.yaml`; redeploy/reload. Do not overwrite existing customizations. The schema ID determines the custom filename: `luna_pinyin_simp` uses `luna_pinyin_simp.custom.yaml`, not `luna_pinyin.custom.yaml`. Full instructions and an English quick start are in [INSTALL.md](INSTALL.md); see also the [manual integration guide](docs/manual-integration.md) for Luna Pinyin and existing `__patch` lists.

Enable **诗Emoji开** in the Ctrl + grave switcher menu. Only the highlighted full Chinese candidate shows a preview; other rows stay unchanged. Option+Return commits the highlighted candidate plus its main emoji; Control+Option+Return chooses the optional edgy preview. Tab always keeps the host schema's behavior. Committing and Escape do not disable the plugin.

Defaults: original skin color, gender-neutral, edgy associations off. Female + medium skin can turn 开发 into `开发 👩🏽‍💻`; explicit gender wording is preserved. Only variants in the pinned Unicode inventory are emitted; mixed multi-person skin tones are not generally transformed.

## Honest boundaries

- Not a runtime semantic model. Missing vocabulary, ambiguity, sarcasm and negation can produce wrong or absent suggestions. Real-estate development may still trigger a programmer.
- Word guards reduce substring errors, but can also suppress useful compound-word matches.
- Chinese interpretation belongs to the host schema. Each full candidate is matched independently; partial-word candidates are not treated as complete sentences.
- Thousands of phrases and lexical entries for 1,906 base Emoji do **not** establish contextual reachability or semantic accuracy.
- Engineering/regression checks are not an independent semantic benchmark. Broad accuracy, other platforms and long-running resource behavior remain unverified.
- Edgy associations cover innuendo, dark humor and stylized violent expressions. They are not a content filter or age classification of words/emoji. Ordinary action meanings remain in the main dictionary.

## Develop and contribute

See [architecture and build commands](docs/architecture.md), [mapping provenance](docs/mapping-resolution.md) and [contribution rules](CONTRIBUTING.md). Bring anonymized real examples, not private chats or personal user dictionaries. Once an example informs dictionary tuning, it is a regression example—not a blind test.

## Licensing

[MIT](LICENSE) covers original project code and rules. Generated data also adapts Unicode-3.0 and jieba MIT data; retain [third-party notices](THIRD_PARTY_NOTICES.md) and `licenses/` when redistributing. No model weights or third-party emoji artwork are shipped. This is an independent project, not an official Rime integration.
