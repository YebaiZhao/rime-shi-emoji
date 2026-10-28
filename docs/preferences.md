# 表情偏好与重口联想配置

肤色、性别与重口联想在当前中文方案的 `.custom.yaml` 中设置，不占用 Rime 原生菜单；默认菜单只保留诗Emoji总开关，启用 `0` 键实验时可加一个输出方式开关。两账号可共用静态配置，但各账号仍须分别重新部署／重启输入法，菜单选择也分别保存。

下文的 74 项是该功能完成时的历史检查数；当前版本检查见 [发布工程](release-engineering.md)。

## 方案配置

在当前中文方案的 `.custom.yaml` 的 `patch:` 下修改以下值；例如万象是 `wanxiang.custom.yaml`。不要改自动生成的 `build/` 文件。

```yaml
  "shi_emoji/skin": default
  "shi_emoji/gender": neutral
  "shi_emoji/adult": true
```

- 肤色：原色（默认）、浅、中浅、中、中深、深。
- 性别：中性（默认）、女性、男性。
- 重口联想：开启（默认）、关闭。统一安装包内已包含相关文件，无需另装。

对应值分别为 `default | light | medium_light | medium | medium_dark | dark`、`neutral | female | male`、`false | true`。改完重新部署并重载；无需改动主开关。默认情况下 `default.custom.yaml` 只需保存 `shi_emoji` 总开关；若启用 [0 键实验](experimental-zero-key.md)，还要保存 `shi_emoji_emoji_only`。两个账号的菜单选择分别记忆。旧版 `shi_emoji_skin_*`、`shi_emoji_gender_*`、`shi_emoji_adult` 菜单及保存项应从自定义补丁移除。

## 变体规则

`python -m shi_emoji.preferences` 从固定 Unicode 16.0 全量目录生成变体表，而非现场拼接字符。只输出目录内合法序列。性别、肤色选择作用于本插件增强后缀，不修改原文或宿主候选。

例如“开发”可从 🧑‍💻 变为 👩🏽‍💻。“女科学家”“男科学家”等明确性别表达保留原映射的性别，仅应用可用肤色。性别显式判断目前基于中文关键词，不是完整语义理解。不支持的性别或肤色组合保留可用基础表情；显式组合如 🐂🍺 不拆改。多人混合肤色未统一替换；Unicode 合法也不保证旧系统字体都能显示。

## 重口联想扩展

详见 [开关范围](adult-addon.md)。统一安装包内包含独立的映射模块，默认开启，不需要额外下载。设为 `false` 后不加载、不查询；开启后建立的索引可缓存，但关闭并重载后不查询。主开关关闭或英文模式同样阻止查询。

保持 `shi_emoji/adult: true` 时，仅在当前高亮候选旁分别显示主库和重口预览，不新增候选行。⌥+回车提交主库结果，⌃⌥+回车提交重口结果；Tab 保留万象原有行为。另行启用[实验候选槽](experimental-candidate-slot.md)时，数字键可只提交主库 Emoji。统一安装包中的扩展文件缺失或语法损坏属于安装错误，会明确报错，不再伪装成可选安装。它不是主库或其他输入法的内容过滤器。

当前有 140 个输入短语、38 组联想；它们覆盖一批常见说法，不代表任意长句都能正确理解。短而多义的词仅在整条候选精确匹配时触发，减少普通语境误联想。

普通动作表达不受该开关控制。“暴打、揍人、挨揍、打架、挥拳、挥拳头”现有主库本义映射 👊/🤜/🤛；“拳击”原有 🥊 映射保留。例如“万圣节暴打小朋友”增强为 `🎃 👊 🧒`，女性偏好下为 `🎃 👊 👧`。这些是已知回归例，不作为整体语义质量指标。

此前版本曾通过 74 项完整检查；该数字不是本次预览交互改造的测试结果。运行时行为以当前版本回归测试和安装后实测为准。

## 构建与验证

```sh
PYTHONPATH=src python -m shi_emoji.preferences
python scripts/package_runtime.py
python scripts/prepare_wanxiang_probe.py --source /path/to/compiled/rime --output dist/preferences-probe
python scripts/check_release.py --profile dist/preferences-probe
```

测试覆盖生成序列合法性、显式性别、肤色、不支持的组合、重口联想静态关闭/开启、ZIP 内置扩展，以及总开关跨进程记忆。输入拼音的“sese”在当前隔离词典中优先解释为“瑟瑟”；移到“色色”时才在它旁边显示重口预览，不会把“色色”的联想套在“瑟瑟”上。
