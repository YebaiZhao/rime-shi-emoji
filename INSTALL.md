# 安装诗Emoji

[项目介绍](README.md) · [偏好说明](docs/preferences.md) · [English quick start](#english-quick-start)

## 环境与文件

需要带 **librime-lua（Lua 5.4）** 的 Rime 前端和一个正常工作的中文方案。当前主要验证 macOS 鼠须管 + 万象全拼；其他方案不能直接假定兼容。普通用户不需要 Python、模型、账号或后台服务。

使用统一的 `rime-shi-emoji-runtime.zip`。包内有 Lua、两份配置例、说明及许可证；重口联想文件已包含，但默认关闭。`MANIFEST.sha256.json` 用于文件一致性检查，不是数字签名。

## 1. 放置插件

鼠须管菜单 →「用户设定」打开 Rime 用户目录（通常为 `~/Library/Rime`）。将解压文件夹里的 **`lua/shi_emoji`** 放进该目录的 `lua` 下，最终应有 `lua/shi_emoji/filter.lua`、`variants.lua`、`variant_data.lua`、`adult.lua` 等八个 Lua 文件。

不要复制成 `lua/shi_emoji/shi_emoji`，不要覆盖整个 `lua` 目录，保留其他插件。

## 2. 合并中文方案补丁

找到当前方案 ID。例如万象的 `wanxiang.schema.yaml` 中 `schema/schema_id` 为 `wanxiang`，对应用户文件 **`wanxiang.custom.yaml`**。其他方案使用自己的 ID。

将包内 `shi_emoji_phrase.custom.yaml.example` 的条目合并到已有的 `patch:` 下。不要直接覆盖配置，也不要编辑自动生成的 `build/`。

```yaml
patch:
  "engine/processors/@before 0": lua_processor@*shi_emoji.processor
  "engine/filters/+":
    - lua_filter@*shi_emoji.filter
  "switches/+":
    - name: shi_emoji
      states: [诗Emoji关, 诗Emoji开]
    - options: [shi_emoji_skin_default, shi_emoji_skin_light, shi_emoji_skin_medium_light, shi_emoji_skin_medium, shi_emoji_skin_medium_dark, shi_emoji_skin_dark]
      states: [原色肤色, 浅肤色, 中浅肤色, 中肤色, 中深肤色, 深肤色]
    - options: [shi_emoji_gender_neutral, shi_emoji_gender_female, shi_emoji_gender_male]
      states: [中性表情, 女性表情, 男性表情]
    - name: shi_emoji_adult
      states: [重口联想关, 重口联想开]
```

已有相同 patch 键时，合并列表项，不能重复写 YAML 键。若已有插件占用 `engine/processors/@before 0`，按原方案调整插入位置，保留两者；诗Emoji processor 放前面，filter 放末尾。自定义末尾过滤器可能影响候选结果，需要自行验证。

## 3. 保存菜单状态

在另一个文件 **`default.custom.yaml`** 的已有 `patch:` 下，合并 `shi_emoji.default.custom.yaml.example`：

```yaml
patch:
  "switcher/save_options/+":
    - shi_emoji
    - shi_emoji_skin_default
    - shi_emoji_skin_light
    - shi_emoji_skin_medium_light
    - shi_emoji_skin_medium
    - shi_emoji_skin_medium_dark
    - shi_emoji_skin_dark
    - shi_emoji_gender_neutral
    - shi_emoji_gender_female
    - shi_emoji_gender_male
    - shi_emoji_adult
```

不要给这些开关增加 `reset`，否则可能覆盖已保存的选择。

## 4. 部署、开启

鼠须管菜单 →「重新部署」，完成后重载输入法。Ctrl + 反引号打开方案选单，选中「诗Emoji关」切到「诗Emoji开」。布尔开关显示的是当前状态；如果选项被折叠，先展开那一行。

试输入“开发”：当前高亮候选旁会显示 `〔诗Emoji 🧑‍💻〕`，其他候选不显示本插件预览。空格提交普通中文；高亮想要的候选，按 Option/⌥ + 回车才提交“原文 + Emoji”。例如输入 `xiaren`，移动到“虾仁”，看到 🦐 🍤 后再按 ⌥+回车，就会提交“虾仁 🦐 🍤”。女性 + 中肤色可让“开发”预览 👩🏽‍💻。Tab 始终执行万象原有功能；提交、Esc 不关闭插件。

性别、肤色和重口联想详见 [偏好说明](docs/preferences.md)。重口联想开启时只在高亮候选旁另显示“重口”预览，使用 Control/⌃ + Option/⌥ + 回车提交；不会额外占用候选行。

如果愿意让数字键只上屏跟随高亮的 Emoji，可另行启用[实验候选槽](docs/experimental-candidate-slot.md)；它会把每页上限设为 7，且没有联想时普通第 7 候选仍可能出现。默认安装不更改每页候选数量。

## 更新与卸载

- **更新**：用新版包替换本插件的八个 Lua 文件，保留其他 Lua 文件与个人词库。对照两份配置例，仅补新增条目，不重复添加已有组件或开关；重新部署、重载。
- **旧临时模式迁移**：移除旧 `shi_emoji/hotkey` 与 `reset`；不再使用 Ctrl+Shift+E。早期 `semantic_emoji` 组件需从配置中移除，不与现行组件同时启用。
- **双账号**：可以共享静态文件，但两个账号分别部署、分别保存菜单状态。共享目录权限由本机管理者设置，插件不会自动修改权限。
- **卸载**：先移除 schema 中本插件的两个组件、四个设置组，以及 `default.custom.yaml` 中全部 `shi_emoji`/`shi_emoji_*` 保存项。保留其他项目；部署、重载后再移除 `lua/shi_emoji`。不要删除整个 Rime 目录或用户词库。

## 排障

| 现象 | 先检查 |
|---|---|
| 菜单没有诗Emoji | schema ID 是否正确、补丁是否合并成功、是否重新部署 |
| 菜单有但没有预览 | 主开关是否开启、是否中文模式、先用“开发/牛逼”检查；陌生表达可能未覆盖 |
| 字体方框或缺字 | 系统 Emoji 字体是否支持该 Unicode 序列，旧系统可能缺少新表情 |
| 重启后偏好丢失 | 保存项是否完整、是否误加 `reset`、是否在另一个账号下 |
| 部署报 YAML 错误 | 缩进、重复 patch 键、是否覆盖了原配置；不要修改 `build/` 掩盖错误 |

报告时提供前端/方案版本、拼音、实际中文候选和期望表情；先去掉隐私，不上传用户词库或完整私人配置。

## English quick start

Use a Rime frontend with librime-lua / Lua 5.4. macOS Squirrel + Wanxiang full pinyin is the primary tested setup.

Copy the eight files in `lua/shi_emoji` into your Rime user directory without replacing other plugins. Merge `shi_emoji_phrase.custom.yaml.example` into the current Chinese schema's custom file and `shi_emoji.default.custom.yaml.example` into `default.custom.yaml`. Preserve existing patches and avoid duplicate YAML keys. Redeploy/reload, then enable **诗Emoji开** in the native Ctrl+grave menu.

Candidate order stays unchanged. Only the highlighted Chinese candidate shows an emoji preview; press Option+Return to commit text plus the main emoji, or Control+Option+Return for the optional edgy preview. Tab keeps the host schema's behavior and Space still commits plain Chinese. Defaults: original skin, neutral gender, edgy associations off. All files are in one ZIP. To upgrade, replace only this plugin's files and merge new settings. To uninstall, remove its two components, all four setting groups and all `shi_emoji*` save-options, redeploy, then remove only this plugin's folder. No user dictionary deletion is needed.

When redistributing the runtime, retain `LICENSE`, `THIRD_PARTY_NOTICES.md` and `licenses/` alongside the plugin.
