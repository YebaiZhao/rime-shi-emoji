# 262 项自然入口修复

2026-11-06：原审定报告中一般／发散档没有自然名称输出的 **262 项已修复**。其中 258 项补映射，😗／😳 调整排序，👴／👵 修正明确性别称呼被中性偏好改写的问题。固定分母 1,906 项全量复查后，一般／发散档均至少有一个已审定自然名称可输出，新增不可达项目为 0。

## 修复范围

- 原 262 项覆盖 **495 个不同名称、496 个名称—目标组合**，这些名称在一般及发散档均能输出所审定的目标。
- 补一个保留入口“害羞的笑脸 → 😊”：将“微笑”中的 🙂 提前后，原两项输出上限会挤掉 😊；通过已经审定的区别性名称保留可达性。总计 **496 个完整候选入口、497 个补充名称—目标组合**。
- 新名称从一般档起生效。已有严格关系保留原档位，不把全部新名称升级为严格关系。
- “亲亲 → 😗 😘”“亲吻 → 😗 💏”“脸红 → 😳 ☺️”。原来的其他精确解释仍保留在关系表中，单概念最多两个输出的限制不变。
- 老头、老爷爷、爷爷、老奶奶、奶奶、老太太遵循名称中的明确性别；肤色偏好继续生效。“老人”继续遵循用户的性别偏好。
- 保留“禁止标志 → 🚫／🈲”“缆车 → 🚠／🚡”“骆驼 → 🐪／🐫”“恐龙 → 🦕／🦖”“红圈 → ⭕／🔴”“滑雪板 → 🎿／🏂”等合理多义。所有被补充词原有的精确目标及档位均保留。

补充关系在 `entry_data.lua` 中按完整中文候选精确查找，不加入子串 trie，也不产生新的完整词保护边界。原 `tier_data.lua`、匹配器和组合器与本次修复前逐字节相同；预览和快捷键提交使用同一个 `filter.suffix` 结果。

## 全量 Lua 对照

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 基础 Emoji 分母 | 1,906 | 1,906 |
| 审定名称全部无一般档输出的项目 | 262 | **0** |
| 审定名称全部无发散档输出的项目 | 262 | **0** |
| 审定名称全部无严格档输出的项目 | 318 | 315 |
| 所有发现词均无一般／发散档入口的项目 | 5 | **0** |
| 审定名称均无精确运行时关系的项目 | 335 | 77 |

最后一项不是输出失败：剩余 77 项已有自然名称通过现有子词关系输出目标，本次没有为它们额外扩表。本轮也不承诺所有 3,468 个已审定名称—目标组合都独立精确收录；原 262 项的全部名称—目标组合已检查通过。

全量检查使用 **14,002 个发现词、20,980 个词—目标组合、42,006 次三档真实 Lua 调用**。逐词比较本次修改前后的实际运行时：13,504 个输入不变，498 个输入有变化，其中 496 个是补充入口，另两个是“爷爷／奶奶”的明确性别修正。

对全部 496 个入口分别嵌入“请查看…的说明”，修复前后仅“老头／老奶奶”按预期从 🧓 改为 👴／👵。另对每个入口的三种句子／否定模板，比较补充表开启与关闭时的结果：1,488 个输入、三档均相同，确认补充表不新增句中触发。全部 497 个补充名称—目标组合还分别检查重口联想开启与关闭时的一般／发散输出。六种肤色 × 三种性别偏好均检查明确称呼和泛称。

## 测试结果

完整测试套件在隔离原生 profile 中运行：**145 项全部通过，0 跳过，0 失败**，含原生开关、预览、快捷键提交、安装／禁用／卸载和解包后加载。结果保存在 [测试日志](../data/reachability/entry-repairs-262/tests.log)。

原生拼音搜索覆盖全部 **496 个名称**；修正“系丝带的心／长棍面包／长鼻子鬼面”的多音字后，**322 个名称找到完全相同的中文候选，322 个预览和 322 个提交全部通过**。另 **174 个名称在前五页未找到**，详见[未找到清单](../data/reachability/entry-repairs-262/native-not-found.tsv)。按原 262 项目标合并，210 项有本次原生提交证据，52 项在这次搜索中未找到任何选定名称候选。这个宿主候选层的限制仍保留，不能据此声称 262 项都已实测拼音上屏。没有为消除这项差异写入宿主词库。

## 可复核资料

- [262 项逐项修复结果](../data/reachability/entry-repairs-262/repairs.tsv)：每项的名称、原因、一般／发散实际输出和原生可达名称。
- [修复清单](../data/entry_repairs_262.json)：原 262 项、全部名称、排序决定及额外保留入口；绑定修复前报告 SHA-256。
- [修复前快照](../data/reachability/natural-name-review/summary.json)：保留历史原件，不以当前报告覆盖。
- [修复后全量摘要](../data/reachability/entry-repairs-262/summary.json)和[逐项入口表](../data/reachability/entry-repairs-262/name-gaps.tsv)。完整证据位于同目录 `entries.jsonl.gz`。
- [前后对照与文件指纹](../data/reachability/entry-repairs-262/comparison.json)及[所有变化输入](../data/reachability/entry-repairs-262/query-diff.jsonl)。修复前是本次开始时的工作树快照，包含此前并行修改，不冒充 alpha.4 原始运行时。
- [原生候选、预览、提交记录](../data/reachability/entry-repairs-262/native.json)：与 Lua 报告分层记录。

## 复现

```sh
PYTHONPATH=src .venv/bin/python -m shi_emoji.tier_export
PYTHONPATH=src .venv/bin/python -m shi_emoji.reachability \
  --natural-names --output data/reachability/entry-repairs-262
PYTHONPATH=src:tests .venv/bin/python -m unittest \
  tests.test_entry_repairs tests.test_natural_names tests.test_package -v
```

原生检查只允许一次性 profile。`--output` 必须为新目录，不能指向活动配置：

```sh
.venv/bin/python scripts/prepare_wanxiang_probe.py \
  --source /path/to/compiled/rime --output /tmp/new-entry-probe \
  --zero-key --no-adult
PYTHONPATH=src .venv/bin/python scripts/probe_entry_repairs.py \
  --profile /tmp/new-entry-probe --pages 5 \
  --output data/reachability/entry-repairs-262/native.json
```

拼音检查使用 `pypinyin` 生成并修正上述三个多音字的全拼，在前五页查找完全相等的中文候选。没有找到表示该查询及页数内未见目标，不断言字典中不存在，也不把 Lua 成功当作拼音可达证据。原生结果是无界面 librime 的候选预览／提交，不等于鼠须管界面与应用插入验收。

本轮没有改活动输入法配置或词库，没有提交、推送、部署或发布。运行时包白名单已纳入 `entry_data.lua`，现在是 11 个 Lua 文件；实际解包加载另有测试。
