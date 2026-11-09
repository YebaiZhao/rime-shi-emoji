# Shi Emoji · 诗Emoji

**Type Chinese as usual. Add emoji when you want.**

Shi Emoji is a local Rime plugin. It shows emoji beside the highlighted Chinese candidate without changing candidate order. It supports Simplified and Traditional Chinese and runs without a network connection or a model.

[Download alpha.4](https://github.com/YebaiZhao/rime-shi-emoji/releases/tag/v0.1.0-alpha.4) · [Installation](INSTALL.md) · [中文](README.md)

## Why try it?

- **Use everyday Chinese, not emoji names.** 收到 can suggest 👌; 虾仁 can suggest 🦐 🍤.
- **Move the highlight to see a different suggestion.** When you move from 吓人 to 虾仁, the emoji beside the highlighted candidate changes.
- **Choose how creative it gets.** Strict favors direct matches, General adds natural associations, and Creative adds more playful ones.
- **Choose what to commit.** Space keeps its normal behavior. Use Option+Return to include emoji, or enable the optional `0` and Option+0 shortcuts to switch quickly between text plus emoji and emoji only.

## Install and try it

**v0.1.0-alpha.4** is a prerelease, tested primarily on macOS Squirrel with Wanxiang Pinyin. See the [manual integration guide](docs/manual-integration.md) for Luna Pinyin. Other frontends need librime-lua and may handle shortcuts differently.

1. Download [`rime-shi-emoji-runtime.zip`](https://github.com/YebaiZhao/rime-shi-emoji/releases/download/v0.1.0-alpha.4/rime-shi-emoji-runtime.zip). Extract it and copy `lua/shi_emoji` into the `lua` folder in your Rime user directory. No source checkout or Python installation is needed.
2. Merge the two YAML examples into your schema's `*.custom.yaml` and `default.custom.yaml` as shown in [INSTALL.md](INSTALL.md). Keep your existing settings.
3. Redeploy. In Chinese mode, open the menu with **Ctrl + grave**, turn on **诗Emoji开**, and select **诗Emoji一般** (General).
4. Type `xiaren`, highlight 虾仁, and press **Option+Return** once 🦐 🍤 appears. Space still commits plain text.

## Commit with 0 and change settings

The plugin leaves `0` alone by default. Follow the [0-key setup](docs/experimental-zero-key.md) to enable it and add the output-mode switch, then redeploy. Do not enable the numbered candidate slot at the same time.

When the highlighted candidate shows `〔0→…〕`, use the main keyboard `0`:

| Current output mode | `0` | Option+0 |
|---|---|---|
| 原文＋Emoji (text + emoji, default) | 虾仁 🦐 🍤 | 🦐 🍤 |
| 仅Emoji (emoji only) | 🦐 🍤 | 虾仁 🦐 🍤 |

Without the `0→` hint, your schema handles `0` as usual. With these shortcuts enabled, Option+Return is an alias for Option+0.

In the **Ctrl + grave** menu, expand settings if folded. Select **诗Emoji一般 / 诗Emoji严格 / 诗Emoji发散** for General, Strict, or Creative. Selecting the on/off or output-mode row toggles its current value.

Skin tone, gender, and edgy associations are set in your [schema configuration](docs/preferences.md). In alpha.4, the separate `〔重口 …〕` hint uses Control+Option+Return, not `0`. Unreleased changes merge these associations into Creative and use the regular commit keys.

## Feedback and contributing

Local dictionaries can miss new expressions or misread context. When reporting a match, include the pinyin, the Chinese candidate, and the actual and expected emoji. Please leave out private messages and user dictionaries.

[Contributing](CONTRIBUTING.md) · [How it works](docs/architecture.md) · [Mapping sources](docs/mapping-resolution.md) · [Changelog](CHANGELOG.md)

Original code and rules use the [MIT license](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for derived data. This is an independent plugin, not an official Rime component.
