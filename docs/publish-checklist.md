# 首次 GitHub 发布前清单

版本目标：`v0.1.0-alpha.1`（prerelease）。源码提交／推送不等于创建标签或 GitHub Release；各步骤按实际远端状态核对。

## 本地已准备

- 中英文 README、当前安装/卸载、能力边界、贡献规范和反馈表单。
- MIT 原创代码声明、Unicode/jieba 原始许可和第三方来源说明；无权重及 Emoji 图片。
- 统一运行时 ZIP、逐文件清单、版本元数据、外部 SHA-256 文件。
- 模型历史审核产物与摘要保持不变，未伪造新审核。
- 独立 profile 的完整检查、ZIP 生命周期和文档一致性检查。
- [GitHub About / Topics 文案](github-listing.md) 与 [Release 正文](release-notes.md)。

## 仍需实际执行或确认

- 核对实际提交文件，确认没有个人配置、密钥、userdb、模型权重或虚拟环境；原始模型预测约 30 MB，作为可追溯源码数据保留，但未进入运行时 ZIP。
- 核对 GitHub 仓库所有权、可见性、源码推送结果；`origin` 为 `YebaiZhao/rime-shi-emoji`，是否已发布 Release 另查。
- 实际跑一次远端 CI。Linux CI 是便携检查，不包含完整 macOS 原生 Rime 验收。
- 若准备创建 GitHub Release，再创建标签、上传通用运行时 ZIP 及 `SHA256SUMS`，标记 prerelease；仅推送源码时不要宣称已发布 Release。
- 完成独立用户或机器的手工安装、配置合并与升级试用；Alpha 不应被宣传为稳定版或全平台已验证。

公开前不必捏造准确率或拼接“好评”。让用户在首页快速看到示例、安装成本、限制和反馈入口，比承诺任意语义理解更可靠。
