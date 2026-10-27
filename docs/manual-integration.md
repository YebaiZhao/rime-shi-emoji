# 手动接入朙月拼音与其他 Rime 中文方案

先按[安装指南](../INSTALL.md)把九个 Lua 文件放进用户目录。这里说明如何在不覆盖原有配置的情况下，接入一个已有的中文方案。本文只在 macOS 鼠须管的朙月拼音、朙月拼音·简化字上做过配置编译验证；目前词库主要按**简体候选词形**整理，繁体模式下能安装但很多词不会命中。其他前端可参考相同的 Rime 补丁结构，但不保证快捷键或候选界面一致。

## 找对文件：按方案 ID，不按显示名

| 方案显示名 | 方案 ID | 用户目录里的补丁文件 |
|---|---|---|
| 万象拼音 | `wanxiang` | `wanxiang.custom.yaml` |
| 朙月拼音·简化字 | `luna_pinyin_simp` | `luna_pinyin_simp.custom.yaml` |
| 朙月拼音 | `luna_pinyin` | `luna_pinyin.custom.yaml` |

其他方案打开其 `*.schema.yaml`，读 `schema/schema_id`；再在 Rime 用户目录创建同名 `ID.custom.yaml`。用户目录请从前端菜单／设置入口打开，不要编辑部署生成的 `build/`。一台电脑有多个系统账户时，每个账户都要在自己的 Rime 用户目录部署；共享 Lua 和补丁文件不等于共享已编译配置或开关状态。

## 最短路径：只在一个方案启用

如果该方案没有 `.custom.yaml`，直接以[安装指南第 2 步](../INSTALL.md#2-合并中文方案补丁)的整个 `patch:` 代码块新建文件。如果已有 `patch:`，只把代码块中缩进两格的项目并入原来的 `patch:`，**不要再写第二个 `patch:`**。原有同名列表键（例如 `"engine/filters/+"` 或 `"switches/+"`）应合成一个列表；原有不同键保持不动。再按第 3 步给 `default.custom.yaml` 添加保存项，重新部署。

只用「朙月拼音·简化字」时，目标就是 `luna_pinyin_simp.custom.yaml`。即使文件中已有 `"switches/@next"`、`emoji_suggestion` 等内容，也不要删掉它们；把诗Emoji的 processor、filter、三个静态设置和 `"switches/+"` 加在同一个 `patch:` 下。只用「朙月拼音」且补丁文件没有特殊结构时，同理用 `luna_pinyin.custom.yaml`，但请先切到它的简体输出模式试用；繁体输出的词形覆盖目前不足。

朙月拼音的基础方案可能被简化字方案继承，**不要不加区分地把完整补丁复制到两个文件**，否则可能重复注册组件。若已经在 `luna_pinyin.custom.yaml` 中接入，再想同时启用简化字方案，应先检查部署后的 `build/luna_pinyin_simp.schema.yaml` 中 processor/filter 是否已经继承；简化字方案有自己的 `switches`，即使继承了组件，仍要把 `shi_emoji` 主开关加到它的 `switches/+`。不熟悉继承关系时，先只启用实际使用的一个方案。

## 已有 `__patch` 列表的朙月拼音

部分用户的 `luna_pinyin.custom.yaml` 是 `__patch:` 列表，里面已有 `- patch/+` 或 `__include`。保留该列表，在末尾增加一个 `- patch/+` 项，内容如下；**不要用新的顶层 `patch:` 覆盖这类文件**。

```yaml
__patch:
  # 保留这里原有的其他条目；只追加下面这一项。
  - patch/+:
      "engine/processors/@before 0": lua_processor@*shi_emoji.processor
      "engine/filters/+":
        - lua_filter@*shi_emoji.filter
      "shi_emoji/skin": default
      "shi_emoji/gender": neutral
      "shi_emoji/adult": false
      "switches/+":
        - name: shi_emoji
          states: [诗Emoji关, 诗Emoji开]
```

这段是**追加结构示意**，不是可覆盖整个现有文件的模板。如果原列表已有同一 `patch/+` 且使用相同键，把列表项合进去，避免重复 YAML 键。最安全的检查是重新部署后打开 `build/ID.schema.yaml`：`engine/processors` 有一次 `lua_processor@*shi_emoji.processor`，`engine/filters` 有一次 `lua_filter@*shi_emoji.filter`，`switches` 有一次 `shi_emoji`，并且原方案组件仍在。

## 原方案已有 Emoji 插件时

朙月拼音的某些配置会启用 `emoji_suggestion`：它是独立功能，可能在普通候选里额外产生 Emoji；诗Emoji只给高亮候选加预览，因此同一个词可能看见两种 Emoji 表现。这不是诗Emoji安装了两次。可先保留两者试用，再按原插件的说明决定是否关闭它；不要为了消除重复而删除不认识的过滤器或整个 `switches` 列表。

## 按键与验证

默认模式不改每页候选数，也不改原方案的数字键。在**简体中文模式**打开「诗Emoji开」，输入 `kaifa` 并高亮“开发”：应看到 🧑‍💻 预览；普通空格上屏原文，macOS ⌥+回车上屏「开发 🧑‍💻」。若候选是“開發”，该例不会命中，先检查是否处于繁体输出模式。想让主键区 `0` 只上屏 Emoji，可再按[实验 `0` 键](experimental-zero-key.md)配置；它会接管命中时原方案的 `0` 功能，所以需要自行确认方案是否用 `0` 输入声调或选词。不要同时启用[第 7 项候选槽](experimental-candidate-slot.md)。

部署后菜单没有开关：先查方案 ID 和 `switches`；有开关却无预览：查 processor/filter 是否各出现一次、Lua 文件是否放对目录、是否在中文模式；部署报 YAML 错：先找重复 `patch:`、重复键和缩进。修改原配置前留一份自己的副本，排障时不要删用户词库或整个 Rime 目录。
