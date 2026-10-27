# 安装诗Emoji

[项目介绍](README.md) · [朙月／其他方案手动接入](docs/manual-integration.md) · [偏好说明](docs/preferences.md) · [English quick start](#english-quick-start)

## 环境与文件

需要带 **librime-lua（Lua 5.4）** 的 Rime 前端和一个正常工作的中文方案。当前在 macOS 鼠须管 + 万象全拼验证主要功能；朙月拼音的手动补丁另有[可照做的示例](docs/manual-integration.md)。词库主要针对简体候选；繁体候选覆盖不足。其他前端与方案仍需各自验收。普通用户不需要 Python、模型、账号或后台服务。

有 GitHub Release 时，下载统一的 `rime-shi-emoji-runtime.zip`；如果尚无 Release，也可在仓库网页用 **Code → Download ZIP** 下载源码，不用安装 Python。两种 ZIP 的目录层级不同：

| 下载来源 | 插件文件夹 | 配置例所在位置 |
|---|---|---|
| Release 运行时 ZIP | `lua/shi_emoji` | ZIP 根目录 |
| GitHub 源码 ZIP | `rime/lua/shi_emoji` | `rime/` |

运行时包内有 Lua、两份配置例、说明及许可证；重口联想文件已包含，但默认关闭。`MANIFEST.sha256.json` 用于文件一致性检查，不是数字签名。只需复制上述插件文件夹和合并配置例，不要把源码 ZIP 整包放进 Rime 用户目录。

## 1. 放置插件

从所用 Rime 前端打开其**用户目录**；鼠须管菜单的「用户设定」通常打开 `~/Library/Rime`。将上表对应的 **`shi_emoji` 文件夹**放进用户目录的 `lua` 下，最终应有 `lua/shi_emoji/filter.lua`、`settings.lua`、`variants.lua`、`adult.lua` 等九个 Lua 文件。

不要复制成 `lua/shi_emoji/shi_emoji`，不要覆盖整个 `lua` 目录，保留其他插件。

## 2. 合并中文方案补丁

找到当前方案 ID，而不是界面显示名。例如万象是 `wanxiang`，朙月拼音·简化字是 `luna_pinyin_simp`，分别对应用户目录中的 `wanxiang.custom.yaml`、`luna_pinyin_simp.custom.yaml`。文件不存在就新建；存在就合并，不能覆盖原文件。朙月拼音、已有 `__patch` 或想同时启用两个方案，请先看[手动接入指南](docs/manual-integration.md)。

将上表所指位置的 `shi_emoji_phrase.custom.yaml.example` 条目合并到已有的 `patch:` 下。不要直接覆盖配置，也不要编辑自动生成的 `build/`。

```yaml
patch:
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

已有相同 patch 键时，合并列表项，不能重复写 YAML 键。若已有插件占用 `engine/processors/@before 0`，按原方案调整插入位置，保留两者；诗Emoji processor 放前面，filter 放末尾。自定义末尾过滤器可能影响候选结果，需要自行验证。

肤色、性别、重口联想都在这份方案配置里修改，具体可选值见[偏好说明](docs/preferences.md)。改完需重新部署并重载输入法；菜单里只保留诗Emoji总开关。

## 3. 保存总开关状态

在另一个文件 **`default.custom.yaml`** 的已有 `patch:` 下，合并 `shi_emoji.default.custom.yaml.example`。这一步只负责记住总开关；暂时不加也能当次使用，但重启后可能回到关闭状态。

```yaml
patch:
  "switcher/save_options/+":
    - shi_emoji
```

不要给总开关增加 `reset`，否则可能覆盖已保存的选择。

## 4. 部署、开启

鼠须管菜单 →「重新部署」，完成后重载输入法。Ctrl + 反引号打开方案选单，选中「诗Emoji关」切到「诗Emoji开」。布尔开关显示的是当前状态；如果选项被折叠，先展开那一行。

试输入“开发”：当前高亮候选旁会显示 `〔诗Emoji 🧑‍💻〕`，其他候选不显示本插件预览。空格提交普通中文；高亮想要的候选，在 macOS 按 Option/⌥ + 回车提交“原文 + Emoji”。例如输入 `xiaren`，移动到“虾仁”，看到 🦐 🍤 后再按 ⌥+回车，就会提交“虾仁 🦐 🍤”。其他前端通常对应 Alt+回车，但须以实际按键传递为准。女性 + 中肤色可让“开发”预览 👩🏽‍💻。Tab 保留原方案功能；提交、Esc 不关闭插件。

性别、肤色和重口联想详见 [偏好说明](docs/preferences.md)。重口联想开启时只在高亮候选旁另显示“重口”预览，使用 Control/⌃ + Option/⌥ + 回车提交；不会额外占用候选行。

如果想用一个键只上屏 Emoji，可选[实验 `0` 键](docs/experimental-zero-key.md)；它不新增候选行，但命中时会接管原方案的 `0` 键行为。另一种[实验候选槽](docs/experimental-candidate-slot.md)会改变候选页大小及数字选词行为。两者都不是通用默认值，先检查与当前方案的按键冲突，不要同时启用。

## 更新与卸载

- **更新**：用新版包替换本插件的九个 Lua 文件，保留其他 Lua 文件与个人词库。对照两份配置例，仅补新增条目，不重复添加已有组件或开关；旧版肤色、性别和重口菜单项及其保存项应移除；重新部署、重载。
- **旧临时模式迁移**：移除旧 `shi_emoji/hotkey` 与 `reset`；不再使用 Ctrl+Shift+E。早期 `semantic_emoji` 组件需从配置中移除，不与现行组件同时启用。
- **双账号**：可以共享静态文件和这三个配置值，但两个账号分别部署、分别保存总开关状态。共享目录权限由本机管理者设置，插件不会自动修改权限。
- **卸载**：先移除 schema 中本插件的两个组件、总开关和三个配置值，以及 `default.custom.yaml` 中 `shi_emoji` 保存项。保留其他项目；部署、重载后再移除 `lua/shi_emoji`。不要删除整个 Rime 目录或用户词库。

## 排障

| 现象 | 先检查 |
|---|---|
| 菜单没有诗Emoji | schema ID 是否正确、补丁是否合并成功、是否重新部署 |
| 朙月简化字没效果 | 是否误改了 `luna_pinyin.custom.yaml` 而没给 `luna_pinyin_simp` 的独立 `switches` 加主开关；见[手动接入](docs/manual-integration.md) |
| 同时出现两个 Emoji 结果 | 原方案可能已有 `emoji_suggestion` 等独立插件；先确认是哪一项产生的，不要重复加入诗Emoji组件 |
| 菜单有但没有预览 | 主开关是否开启、是否中文模式、先用“开发/牛逼”检查；陌生表达可能未覆盖 |
| 字体方框或缺字 | 系统 Emoji 字体是否支持该 Unicode 序列，旧系统可能缺少新表情 |
| 重启后总开关丢失 | `shi_emoji` 保存项是否存在、是否误加 `reset`、是否在另一个账号下 |
| 改了肤色等配置但未生效 | 是否改对当前方案的 `.custom.yaml`、是否重新部署并重载 |
| 部署报 YAML 错误 | 缩进、重复 patch 键、是否覆盖了原配置；不要修改 `build/` 掩盖错误 |

报告时提供前端/方案版本、拼音、实际中文候选和期望表情；先去掉隐私，不上传用户词库或完整私人配置。

## English quick start

Use a Rime frontend with librime-lua / Lua 5.4. macOS Squirrel + Wanxiang full pinyin is the primary tested setup.

Copy the nine files in `lua/shi_emoji` into your Rime user directory without replacing other plugins. Merge `shi_emoji_phrase.custom.yaml.example` into the current Chinese schema's custom file and `shi_emoji.default.custom.yaml.example` into `default.custom.yaml`. Preserve existing patches and avoid duplicate YAML keys. Skin, gender and edgy associations are static schema settings; only the main switch appears in the native Ctrl+grave menu. Redeploy/reload, then enable **诗Emoji开**.

Candidate order stays unchanged. Only the highlighted Chinese candidate shows an emoji preview; press Option+Return to commit text plus the main emoji, or Control+Option+Return for the optional edgy preview. Tab keeps the host schema's behavior and Space still commits plain Chinese. Defaults: original skin, neutral gender, edgy associations off. All files are in one ZIP. To upgrade, replace only this plugin's files and merge new settings. To uninstall, remove its two components, all four setting groups and all `shi_emoji*` save-options, redeploy, then remove only this plugin's folder. No user dictionary deletion is needed.

When redistributing the runtime, retain `LICENSE`, `THIRD_PARTY_NOTICES.md` and `licenses/` alongside the plugin.
