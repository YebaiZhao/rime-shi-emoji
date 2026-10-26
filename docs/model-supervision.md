# 模型建库与监督记录 · 2026-10-26

## 本轮方式

用已缓存的 `paraphrase-multilingual-MiniLM-L12-v2` 实际运行批量建库，固定 revision 为 `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`。输入来自固定 commit 的 Unicode CLDR 中文 Emoji 注释、jieba 常用词频/POS 表和项目原创语境，下载地址、SHA-256、许可都已保存。

原始 100 类、659 个人工短语保留为监督优先层，不改称模型产物。外部已有别名和模型新增语义匹配分开统计。模型在开发构建时运行，用户端仍只运行 Lua 短语检索。

## 实际发现与修正

第一版把整段关键词串编码后，出现“大风/水牛”吸收无关词的高分偏差。丢弃该版输出，改为分别编码名称、关键词与语境短语，做均值中心化和归一化，再取每个 Emoji 的最佳视图。

进一步只保留至少两个字的语义视图，以避免“母亲”被“母 → 瓢虫”误导；只有单字描述时合并为一个描述视图。纯语义扩展还要求完整描述的排名进入前十且相似度不低于 0.5，最佳视图相似度至少 0.88、领先次选至少 0.06。若前两候选来自同一语义短语且两者的完整描述都通过门槛，则保留该语义簇（如“海浪”接近“波浪”，同时匹配 🌊 和 🏄）。同分时用完整描述一致性排序。相似度不是概率，这些门槛只是本轮实验策略。

Codex 逐条阅读了中间版本 318 条通过严格门槛的语义扩展，另查了随机别名样本、边缘分数样本、70 个最终语义簇样本及常用场景。发现“坐落 → 椅子”“机床 → 床”“银川 → 银河”“随机应变 → 随机播放”等望文生义结果，记录为拒绝项。最终新增语义簇未逐条完整复核。

监督修正还包括“周末 → 度假/咖啡”“钓鱼 → 钓竿/鱼”“朋友 → 群体/握手”“您好 → 挥手/微笑”“情节 → 戏剧”“搬家 → 房屋/货车”。这些明确记为 `human-reviewed-override`，由本次助手监督编辑，不冒充纯模型预测。

没有逐条审核全部已有别名，也未测得总体准确率。源注释中的文化联想和歧义仍可能带来奇怪候选。随机样本仅用于找问题，不是独立、盲测的质量分数。

## 可审计产物

- `data/model_predictions.json`：每个查询的模型前五候选、相似度、命中视图、描述一致性及筛选状态。
- `data/everyday_queries.json`：额外收集的日常表达，仅作为模型查询输入，不含指定 Emoji 映射。
- `data/review_policy.json`：门槛、过滤词和监督修改。
- `data/model_phrases.json`：可发布的生成映射及来源标识。
- `data/model_review.json`：本轮审核记录及文件摘要；生成映射变动后必须重新检查并记录。
- `docs/model-review-sample.md`：固定随机种子的语义/别名抽样表。

已有别名命中（`existing-alias`）、语义扩展（`model-thresholded`）和监督修正（`human-reviewed-override`）三类来源分别保存。CLI 构建器会输出各项计数，不将已有关键词命中当作模型泛化能力。

## 重建

```sh
pip install -e '.[build]'
PYTHONPATH=src python -m shi_emoji.sources
PYTHONPATH=src python -m shi_emoji.generate
# 查看结果、修改 review_policy.json 后可重用模型结果：
PYTHONPATH=src python -m shi_emoji.generate --reuse
# 完成实际检查后才记录本轮审核：
PYTHONPATH=src python -m shi_emoji.review --reviewer '你的名字' --summary docs/model-supervision.md
PYTHONPATH=src python -m shi_emoji.export
```

此批处理默认使用本地模型缓存；首次没有缓存时需先按模型卡获取权重。新增常用表达应先进入查询集，再由模型推荐、监督审核。增大词库能提高句中短语覆盖率，但没有让运行时获得任意句子的语义理解能力。
