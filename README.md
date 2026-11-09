# 诗Emoji · Shi Emoji

**正常打中文，顺手带点表情。**

诗Emoji 是 Rime 输入法的插件。它在高亮候选旁显示 Emoji 联想，想用再按键上屏，不用切换输入法。支持简繁中文，全程本地运行。

[下载 alpha.4](https://github.com/YebaiZhao/rime-shi-emoji/releases/tag/v0.1.0-alpha.4) · [安装指南](INSTALL.md) · [English](README.en.md)

## 为什么试试它

- **用平常的说法打出 Emoji**：「收到」可以带出 👌，「虾仁」可以带出 🦐 🍤，不用先想表情叫什么。
- **高亮哪个词，就看哪个词的 Emoji**：用方向键在「吓人」和「虾仁」之间移动，候选旁的联想跟着换，原有候选顺序不变。
- **联想强度有三档**：「严格」以直接对应为主，「一般」增加日常联想，「发散」再加一点创意。随时从输入法选单切换。
- **上屏更灵活**：空格照常提交文字；想带 Emoji 可以按 ⌥+回车，也可以启用 `0` 和 `⌥+0`，在「文字＋Emoji」与「仅 Emoji」之间快速选择。

## 安装并试一次

**v0.1.0-alpha.4** 是预发行版，主要在 macOS 鼠须管＋万象全拼验证。朙月拼音可按[方案接入指南](docs/manual-integration.md)安装；其他前端需要支持 librime-lua，实际键位以该前端为准。

1. 下载 [`rime-shi-emoji-runtime.zip`](https://github.com/YebaiZhao/rime-shi-emoji/releases/download/v0.1.0-alpha.4/rime-shi-emoji-runtime.zip)，解压后把 `lua/shi_emoji` 放入 Rime 用户目录的 `lua`。不用下载源码，也不用装 Python。
2. 按[安装指南](INSTALL.md)合并包内两份 YAML 示例：方案设置放进当前中文方案的 `*.custom.yaml`，保存选项放进 `default.custom.yaml`。不要覆盖原有设置。
3. 重新部署。在中文模式按 **Ctrl + 反引号**，打开「诗Emoji」，选「诗Emoji一般」。
4. 输入 `xiaren`，把高亮移到「虾仁」。看到 🦐 🍤 后，按 **⌥+回车**上屏「虾仁 🦐 🍤」。空格仍只提交文字。

## 用 0 键上屏

默认不接管 `0`。按 [0 键配置说明](docs/experimental-zero-key.md)开启 `shi_emoji/zero_key`、加入输出方式开关，再重新部署。不要同时启用第 7 项候选槽。

高亮「虾仁」并看到 `〔0→🦐 🍤〕` 后，用**主键区**的 `0`：

| 选单当前状态 | `0` | `⌥+0` |
|---|---|---|
| 原文＋Emoji（默认） | 虾仁 🦐 🍤 | 🦐 🍤 |
| 仅Emoji | 🦐 🍤 | 虾仁 🦐 🍤 |

没有 `0→` 提示时，`0` 交还原方案。启用这组键后，⌥+回车是 `⌥+0` 的兼容键。

## 切换设置

按 **Ctrl + 反引号**打开选单；如果选项折叠了，先展开。

- **诗Emoji开／关**：选中这一项切换开关。
- **诗Emoji一般／严格／发散**：直接选想用的档位，默认一般。
- **原文＋Emoji／仅Emoji**：启用 `0` 键后才出现。选中这一项切换输出方式，不影响联想档位。

肤色、性别和重口联想在[方案配置](docs/preferences.md)中调整。alpha.4 的 `〔重口 …〕` 是独立提示，用 `⌃⌥↩` 上屏，不走 `0`。下一版会将这部分并入发散档，统一使用普通上屏键；尚未发布。

## 反馈和贡献

诗Emoji 使用本地词库和匹配规则，可能漏掉新说法，也可能猜错语境。反馈时欢迎附上「输入拼音、实际候选、实际与期望的 Emoji」，不用上传私人聊天或用户词库。

[贡献指南](CONTRIBUTING.md) · [工作原理](docs/architecture.md) · [词库来源](docs/mapping-resolution.md) · [更新记录](CHANGELOG.md)

原创代码和规则采用 [MIT](LICENSE)。派生数据的来源与许可见[第三方声明](THIRD_PARTY_NOTICES.md)。这是独立插件，不是 Rime 官方组件。
