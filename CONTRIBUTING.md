# 贡献指南

最需要的贡献：真实误联想、常见叫法、不同输入方案的兼容性结果。不要求你训练模型。

## 报告问题

提供前端及方案版本、插件版本、拼音输入、实际中文候选、实际/期望表情，以及肤色/性别/重口联想开关状态。不要上传私人聊天、用户词库或包含秘密的完整配置。GitHub Issue 模板会提示这些字段。

## 词库修改放哪里

| 文件 | 用途 |
|---|---|
| `data/literal_aliases.json` | 常见名称、本义及俗称；不自动声称完成语境消歧 |
| `data/lexical_aliases.json` | 人工监督的联想，例如三文鱼→🍣 |
| `data/phrases.json` | 明确表达、固定组合与语义分组，例如牛逼→🐂🍺 |
| `data/adult_phrases.json` | 默认关闭的重口联想扩展；收录明确的性暗示、暗黑梗和夸张暴力表达，不放普通动作或普通食物名称 |
| `data/everyday_queries.json` | 离线模型建库的输入词，不是直接批准的映射 |

写清楚来源、许可、词义/联想类别和取舍原因。不要搬运许可不明的 Emoji 词库，不导入商业图片。明确短语是否应保留指定性别；不要把某种默认性别写成唯一正确答案。

## 构建与检查

Python 3.10+；普通数据导出/打包用标准库。本机原生测试另外需要 PyYAML 和已安装的 Squirrel。详见 [构建指南](docs/architecture.md)。

```sh
PYTHONPATH=src python3 -m shi_emoji.coverage --fetch --check
PYTHONPATH=src python3 -m shi_emoji.wordguards
PYTHONPATH=src python3 -m shi_emoji.export
PYTHONPATH=src python3 -m shi_emoji.preferences
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/package_runtime.py
```

`wordguards` 需要固定版本 jieba 数据，首次获取见构建指南。提交对应的生成产物，但不要提交 `data/upstream`、虚拟环境、活动 profile 或个人 userdb。覆盖预算下降必须解释真实原因，不能只改阈值让 CI 变绿。

涉及离线模型时，使用固定模型 revision、保留预测和监督记录。修改生成映射后实际审查再更新摘要，不能为了通过哈希检查而伪造审核。旧模型词库并非逐条审核。

## 测试不是宣传数字

新增正例也加反例，例如“动车可出高铁，电动车不能误出高铁”。开发时看到或用来调词的样本只算回归例，不再称盲测。独立语义测试需要在版本冻结后使用独立来源；允许“不加表情更合理”。工程测试数量不等于语义准确率。

原生测试只使用准备脚本生成的一次性目录，不能指向活动 Rime 用户目录。性能结论注明环境、样本、冷/热状态及测量范围。

## 提交边界

保持 Python/Lua 匹配行为一致，更新相关用户文档和来源说明。保留 MIT、Unicode-3.0 与第三方通知，不把混合生成词库整体重标为纯原创 MIT。没有要求贡献者转让著作权；提交前请确认你有权按项目相应许可提供贡献。
