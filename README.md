# 诗Emoji · Shi Emoji

**正常打中文，顺手带点表情。**

给 Rime / 鼠须管的中文候选添加 Emoji 预览、按需上屏的轻量插件。不是另一套输入法，也不在打字时运行 AI 模型。

[安装](INSTALL.md) · [朙月／其他方案手动接入](docs/manual-integration.md) · [English](README.en.md) · [工作原理](docs/architecture.md) · [贡献](CONTRIBUTING.md) · [更新记录](CHANGELOG.md)

```text
高亮候选：我不想去海边 〔诗Emoji 🙅 🏖️〕
按 ⌥+回车上屏：我不想去海边 🙅 🏖️
它靠词组匹配与离线整理的联想工作：
牛逼                 → 牛逼 🐂🍺
三文鱼               → 三文鱼 🍣
开发                 → 开发 🧑‍💻
```
## 为什么试试它

- **按平常的说法就能打出 Emoji**：比起只搜原生 Emoji 的名称，诗Emoji 的词库更贴近日常中文。「收到」可以带出 👌，「虾仁」可以带出 🦐 🍤，不用先想表情叫什么。
- **高亮哪个词，就看哪个词的 Emoji**：候选顺序不变。用方向键在「吓人」和「虾仁」之间移动，高亮项旁的 Emoji 跟着换。
- **联想强度有三档**：「严格」偏直接对应，「一般」加上自然的日常联想，「发散」再加一点创意。随时从输入法选单切换。
- **上屏方式更灵活**：空格照常上屏纯文字，⌥+回车可以带上 Emoji。启用 [0 键上屏](#用-0-键上屏)后，用 `0` 和 `⌥+0` 在「原文＋Emoji」与「仅Emoji」之间快速选择，还可以在选单对调两键。

全程本地运行，支持简繁中文，不联网、不加载模型。

## 开始使用

从 [v0.1.0-alpha.4](https://github.com/YebaiZhao/rime-shi-emoji/releases/tag/v0.1.0-alpha.4) 下载 **`rime-shi-emoji-runtime.zip`**，即可试用三档联想和 `⌥+0`。不用下载源码，也不用安装 Python。

1. 解压，将 ZIP 中对应的 `shi_emoji` 文件夹放进 Rime 用户目录的 `lua` 下。
2. 合并两份 `.yaml.example`：组件和选单设置放进中文方案的 `*.custom.yaml`（如 `wanxiang.custom.yaml`），保存选项放进 `default.custom.yaml`。不要覆盖已有配置。
3. 重新部署、重载，在 Ctrl + 反引号选单中切到「诗Emoji开」。

完整配置、升级、卸载和排障见 [安装指南](INSTALL.md)；朙月拼音及已有复杂补丁的用户看[手动接入示例](docs/manual-integration.md)。

开启后：只有当前高亮且命中的完整中文候选显示预览，不新增候选行。移动高亮到想要的词，再按 ⌥+回车上屏「该词 + 主库 Emoji」；普通空格仍提交纯文字。Tab 完全保留原方案功能。开启重口联想后，使用 ⌃⌥+回车提交重口预览。提交或 Esc 不会关闭插件。

## 用 0 键上屏

`0` 键默认不接管原方案。先在中文方案的 `*.custom.yaml` 的 `patch:` 下添加以下配置；如果已有 `switches/+`，只把输出选项追加到原列表，**不要重复创建同名键**。

```yaml
  "menu/page_size": 6
  "shi_emoji/candidate_slot": false
  "shi_emoji/zero_key": true
  "switches/+":
    - name: shi_emoji_emoji_only
      states: [原文＋Emoji, 仅Emoji]
```

想记住输出设置，在 `default.custom.yaml` 的 `switcher/save_options/+` 列表追加 `shi_emoji_emoji_only`。重新部署后，在中文模式下启用「诗Emoji开」，输入 `xiaren` 并高亮「虾仁」。看到 `〔0→🦐 🍤〕` 时按**主键区 `0`**：

| 选单当前显示 | 按 `0` | 按 `⌥+0` |
|---|---|---|
| 原文＋Emoji（默认） | 虾仁 🦐 🍤 | 🦐 🍤 |
| 仅Emoji | 🦐 🍤 | 虾仁 🦐 🍤 |

没有预览时，`0` 交还原方案；空格仍只上屏文字。不要同时启用第 7 项候选槽。详见 [0 键配置说明](docs/experimental-zero-key.md)。

## 在输入法选单切换设置

按 **Ctrl + 反引号**打开选单。若设置被折叠，先展开。总开关和输出方式显示当前状态，选中后切换；联想档位直接选你想要的那一档。

- **诗Emoji开／诗Emoji关**：开启或关闭插件。
- **诗Emoji一般／诗Emoji严格／诗Emoji发散**：切换联想档位，默认一般。严格以直接对应为主，一般增加自然联想，发散再加入创意联想。
- **原文＋Emoji／仅Emoji**：切换 `0` 键上屏的内容，不改变联想档位。只有启用 `0` 键实验才出现。

| 设置 | 可选值 | 初始值 |
|---|---|---|
| 诗Emoji | 关 / 开 | 关 |
| 联想档位 | 诗Emoji一般 / 诗Emoji严格 / 诗Emoji发散 | 诗Emoji一般 |
| `0` 键输出（启用实验后） | 原文＋Emoji / 仅Emoji | 原文＋Emoji |
| 肤色 | 原色、浅、中浅、中、中深、深 | 原色 |
| 性别 | 中性、女性、男性 | 中性 |
| 重口联想 | 关 / 开 | 开 |

肤色、性别和重口联想在中文方案的 `.custom.yaml` 中修改，重新部署并重载后生效；`0` 键输出方式仅在启用实验后占用一个方案选单条目，可随时切换。

例如女性 + 中肤色可让「开发」得到 `👩🏽‍💻`；「女科学家」这种明确表达不因男性默认值而被改成男性。只选 Unicode 清单中存在的变体，多人混合肤色未统一处理。

重口联想覆盖性暗示、暗黑梗和夸张暴力表达，详见 [偏好与范围](docs/preferences.md)。

## 能力边界，先说在前面

- **不是实时语义模型**：词库有限，歧义、反讽、双重否定和陌生说法仍可能出错。「房地产开发」仍可能误联想到程序员。
- **繁体是字形别名，不是第二套语义库**：自动转换不保证覆盖所有地区习惯用词，也可能存在一简对多繁的歧义；显式人工词条优先。
- **中文解释由原方案决定**：插件分别匹配每条完整中文候选，不会把首选词的 Emoji 套到其他同音词上。局部候选不会被当成整句匹配。
- **工程测试不是语义盲测**：本机原生 Rime、Lua、安装包和回归检查通过；没有独立总体准确率，也未完成长时间内存与跨平台验收。

## 如何工作

```text
宿主当前高亮候选 → 词组匹配与完整词保护 → 不同概念组合 → 性别/肤色偏好 → 高亮项预览 → ⌥+回车确认
```

模型只在开发阶段帮助提出映射，运行时不参与。词典采用 Unicode CLDR、jieba、人工规则与审核后的模型建议；可用开发命令查看某个词的来源和取舍：

```sh
PYTHONPATH=src python3 -m shi_emoji.match 奶牛 --top-k 20
```

[架构与构建](docs/architecture.md) · [词库来源与合并](docs/mapping-resolution.md) · [评测边界](docs/evaluation.md)

## 一起把它变好

欢迎补充日常叫法、报告误联想、验证其他 Rime 前端。提交前附「拼音输入 / 实际中文候选 / 实际与预期表情」，不要提交私人聊天或用户词库。词义与模型建议必须标明来源；看过并用于调词的例子只算回归集，不再称盲测。

详见 [贡献指南](CONTRIBUTING.md)。项目不自动安装或改写活动 Rime 配置。

## 许可与致谢

原创代码与规则采用 [MIT](LICENSE)。派生词库另包含 Unicode-3.0、jieba MIT 与 OpenCC Apache-2.0 数据，分发时须保留 [第三方声明](THIRD_PARTY_NOTICES.md) 与 `licenses/`；不能把整个生成词库只标成原创 MIT。无模型权重、无第三方 Emoji 图片，图形由系统字体显示。

感谢 [Rime](https://github.com/rime/librime)、[librime-lua](https://github.com/hchunhui/librime-lua)、[Unicode CLDR](https://github.com/unicode-org/cldr-json)、[jieba](https://github.com/fxsjy/jieba) 和 [Sentence Transformers](https://www.sbert.net/)。本项目独立开发，不代表这些项目的官方插件或背书。
