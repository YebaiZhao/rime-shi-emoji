# GitHub 展示信息（复制即可，不会自动发布）

## About description

中文：为 Rime / 鼠须管的中文候选添加 Emoji 预览与按需上屏：本地轻量、无需运行时模型，支持多概念组合、肤色/性别偏好和可开关的重口联想。

English: Local-first emoji candidate enhancement for Rime/Squirrel. Keep Chinese text, add expression. Lua runtime, no AI service; phrase matching, skin/gender preferences and native switches.

## Suggested topics

`rime` `squirrel` `rime-plugin` `librime-lua` `emoji` `chinese-input-method` `pinyin` `lua` `offline` `local-first`

不标“实时 AI 语义搜索”“全平台可用”或准确率数字；当前并没有这些验收证据。只描述已实现能力。

## 首次发布介绍

诗Emoji：正常打中文，顺手带点表情。

默认安装只给当前高亮的中文候选显示 Emoji 预览，不增加候选行；按 ⌥+回车提交「原文＋Emoji」。也可启用实验数字候选槽，按其数字键只提交 Emoji，但会改变万象的 `7` 键用途。不接云端，也不在打字时加载模型。比如「我不想去海边」可联想到 `🙅 🏖️`，「牛逼」可联想到 `🐂🍺`。

这不是“懂一切”的 AI 输入法：目前是离线整理的词组匹配和联想库，语境猜错、没有覆盖都可能发生。首版 Alpha 优先供鼠须管 + 万象全拼试用，欢迎带脱敏例子来改进词库、词边界和其他方案兼容性。

源码、安装指南和已知限制都在仓库首页；普通使用只需要一个运行时 ZIP。

## 发布资产

Releases 标题：`v0.1.0-alpha.1 — 正常打中文，顺手带点表情`

正文使用 [release-notes.md](release-notes.md)。勾选 prerelease；上传 `rime-shi-emoji-runtime.zip` 和 `SHA256SUMS`。同时可上传带版本号的同内容 ZIP，但不需要让用户下载两个。不要上传模型、虚拟环境或本机 Rime profile。

本页只提供文案与元数据建议，不代表仓库已公开、标签已创建或任何社区推广已执行。
