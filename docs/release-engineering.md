# 发布工程核查（不等于语义质量验收）

## v0.1.0-alpha.1 发布候选整理

源码首次提交／推送与 GitHub Release 是两步；本页记录 Alpha 发布候选的工程检查，不把推送源码说成已发布 Release。当前包包含九个 Lua 模块、两份配置示例、中英文说明、[可选候选槽说明](experimental-candidate-slot.md)和许可，所有扩展统一安装。`release.json` 与 Python 版本分别使用 `0.1.0-alpha.1` 和 `0.1.0a1`；测试核对二者的一致性。

新增文档检查：安装 YAML 与示例一致、本地 Markdown 链接有效、许可文件保留、版本元数据一致。打包生成通用及带版本号的同内容 ZIP、内置逐文件清单和外部 `SHA256SUMS`。校验值不是签名。

2026-10-27 的完整本机检查为 95 项、无跳过；另外在一次性 Rime 用户目录中，将通用 `patch:` 接入朙月拼音·简化字、将 `__patch` 列表接入朙月拼音，并验证编译后的 processor/filter/开关各一份。包含已有 `emoji_suggestion` 补丁的朙月简化字配置也在隔离目录编译并显示“开发”预览。繁体“開發”未命中，属于当前简体词形覆盖边界。远端 CI 须在推送后单独核对。这些是工程与指定样例验证，不代表总体语义准确率。下文保留早期发布工程阶段的 62 项测试记录和限制。

早期记录写作时尚未部署或推送；后续本机运行时部署和源码推送都不等于已经发布 GitHub Release。

## 已实现

- 打包使用明确的九个 Lua 文件、文档和两个许可证白名单，避免把临时模块、模型、个人词库混进发布包；测试验证顶层文档链接在 ZIP 中可用。
- ZIP 统一时间戳、排序和权限，同一构建环境、相同内容可逐字节复现。`MANIFEST.sha256.json` 为每个文件记录摘要；它用于一致性校验，不是数字签名。
- 测试直接解压 ZIP 并从其 Lua 目录运行插件，不借用源码 Lua。
- 原生 Rime 生命周期测试从发布包加载插件到新建一次性 profile，验证启用、关闭、移除插件后原候选恢复。该测试适配现有编译 schema；不是从全新操作系统完成 GUI 安装，也未覆盖所有配置合并、升级或前端。
- Lua 测试支持鼠须管内置 Lua 或标准 `liblua5.4`。Linux CI 已配置安装系统 Lua 库，不再因没有 Squirrel 而跳过这些测试；远端 CI 结果仍需按实际运行记录核对。
- 严格本地发布检查遇到任何跳过测试即失败，不能将部分测试成功说成完整验证。

## 复现

现有静态编译资源只读引用，profile 必须新建，不能使用活动输入法目录：

```sh
python scripts/prepare_wanxiang_probe.py --source /path/to/compiled/rime --output dist/release-source-probe
python scripts/check_release.py --profile dist/release-source-probe
python scripts/package_runtime.py
```

profile 必须包含准备脚本生成的 `.shi-emoji-probe` 标记。原生测试需要本机 Squirrel 和 PyYAML；Python 用项目开发虚拟环境。普通用户无需这些工具。

本地 62 项测试通过且无跳过（含 22 个原生行为测试、1 个发布包原生生命周期测试）。这些是工程和回归证据，不是开放语义准确率。

## 尚待完成

- 独立机器及未定制用户配置的手工安装、配置合并、升级验收。
- 真正远端 Linux CI 运行，以及其他 Rime 前端验证。
- 长时间使用内存、首字延迟和异常输入稳定性评测。
- 独立语义盲测和真实试用；已知词库缺口、歧义问题不因工程测试通过而消失。
- 首次源码推送后的 GitHub Actions 结果、提交文件清单与公开可见性复核；创建标签、上传 ZIP 和 `SHA256SUMS`、发布 prerelease 仍是独立步骤。
