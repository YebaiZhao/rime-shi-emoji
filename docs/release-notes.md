# v0.1.0-alpha.1 — 正常打中文，顺手带点表情

首个 Alpha 的当前交互：只在高亮的 Rime 中文候选旁预览 Emoji，不改变候选顺序；按 ⌥+回车提交「原文 + Emoji」，保留万象 Tab 原功能。

另有默认关闭的[实验数字候选槽](https://github.com/YebaiZhao/rime-shi-emoji/blob/v0.1.0-alpha.1/docs/experimental-candidate-slot.md)：槽位随高亮变化，按显示的数字键只上屏 Emoji；启用后每页上限变为 7，万象的 `7` 键用途随之改变。

也可选[实验 `0` 键](https://github.com/YebaiZhao/rime-shi-emoji/blob/v0.1.0-alpha.1/docs/experimental-zero-key.md)：不新增候选行，命中时按 `0` 只上屏 Emoji；会接管该键在宿主方案中的原用途。两种实验二选一，默认都不开启。

## 有什么

- 本地 Lua + 静态数据，无运行时模型、云端 API 或后台服务。
- 句中多个词组组合表情、完整词保护和否定标记。
- 原生选单总开关及配置文件中的肤色/性别偏好，明确性别表达保留原性别。
- 默认关闭的重口联想（性暗示、暗黑梗、夸张暴力表达）；所有文件统一打包。
- 可追溯的数据来源与逐词决策；MIT 原创代码，保留 Unicode/jieba/OpenCC 数据许可。
- 简繁字形共用语义映射；OpenCC 只在构建阶段生成别名，运行时不需要安装。

示例：`我不想去海边 🙅 🏖️`、`牛逼 🐂🍺`、`开发 🧑‍💻`。

## 安装

下载本 Release 的 `rime-shi-emoji-runtime.zip`。按 [安装指南](https://github.com/YebaiZhao/rime-shi-emoji/blob/v0.1.0-alpha.1/INSTALL.md) 复制插件、合并两份配置并重新部署；朙月拼音及复杂补丁见[手动接入](https://github.com/YebaiZhao/rime-shi-emoji/blob/v0.1.0-alpha.1/docs/manual-integration.md)。`SHA256SUMS` 用于下载完整性校验，不是签名。普通用户不需要 Python、OpenCC 或模型。

主要验证环境：macOS 鼠须管 + 万象全拼；朙月拼音·简化字与朙月拼音繁体输出的手动补丁在隔离 profile 中验证过。地区口语词仍可能缺失，其他前端尚待验收。已有本插件用户请按安装指南升级，不重复添加配置。

## 请带着这些预期试用

这不是任意中文语义理解；缺词、多义词、复杂否定和宿主候选错误都可能影响结果。肤色/性别仅应用支持的 Unicode 变体。工程回归通过不等于语义准确率，当前没有独立准确率或长期资源结论。

欢迎反馈脱敏的拼音、实际中文候选与期望表情，或帮忙验证其他 Rime 方案。不要上传个人 userdb 或聊天记录。
