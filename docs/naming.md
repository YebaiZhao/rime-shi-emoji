# 项目命名

- 中文展示名：诗Emoji。
- 英文展示名：Shi Emoji。
- 仓库、项目目录、Python 包分发名：`rime-shi-emoji`。
- Python 模块、Lua 模块、Rime schema/option/config namespace：`shi_emoji`。
- 命令：`rime-shi-emoji`、`rime-shi-emoji-match`、`rime-shi-emoji-export`、`rime-shi-emoji-sources`、`rime-shi-emoji-generate`。

2026-10-26 完成名称迁移。当前账号的万象补丁引用 `shi_emoji.processor` / `shi_emoji.filter`。随后交互已改为原生菜单持久开关、原文第一/增强第二，旧 Ctrl+Shift+E 一次性触发已取消。

本机旧 `semantic_emoji` 模块已按用户要求移除；另一账号需重新部署并重载新配置。测试 fixture 准备脚本能识别旧 namespace 并清理旧组件，只安装一套当前组件。发布包仅含 `shi_emoji`。
