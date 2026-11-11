# 可选的自然名称拼音入口

有些 Emoji 的中文名称已有联想关系，但宿主字典没有完整中文候选，例如“天狗面具”被组句为“舔狗面具”。这个补充为 64 个经逐项审定、未在宿主前五页找到的名称提供完整中文候选。普通空格仍提交中文；高亮该名称后，使用现有快捷键提交 Emoji。

该补充独立于默认配置，不写用户词库，不依靠学习记录。只有显式加入下面的 translator 并开启诗Emoji，才提供这些候选。未命中的输入保持原候选；命中的输入会增加名称候选，因此候选绝对位置可能改变。关闭诗Emoji或进入英文模式时不提供补充候选。

## 接入方式

本次只在隔离 profile 验证，尚未部署到活动输入法。未来需要启用时，先安装包含 `pinyin.lua` 和 `pinyin_data.lua` 的完整插件文件夹，再把 `shi_emoji_pinyin.custom.yaml.example` 合并进现有中文方案的 patch：

```yaml
patch:
  "engine/translators/+":
    - lua_translator@*shi_emoji.pinyin
```

这是主插件配置之外的可选项，不要重复创建 `patch` 或覆盖已有 translators。保存配置后，用户自行重新部署并重载；本轮没有执行这一步。删除这条 translator 即可移除补充，不需要删除任何用户词典。

## 输入方式

输入选定名称的完整拼音，也可以用单引号分隔音节。例如：

| 原未命中名称 | 可用叫法 | 输入 |
|---|---|---|
| 爱心眼 | 花痴 | `huachi` |
| 金钱脸、财迷脸 | 见钱眼开 | `jianqianyankai` |
| 相框画、装框的画 | 画框 | `huakuang` |
| COOL按钮、酷按钮 | 酷标志 | `kubiaozhi` |
| NEW按钮、新款标志 | 新品标志 | `xinpinbiaozhi` |
| 写着SOON的箭头 | 即将到来标志 | `jijiangdaolaibiaozhi` |
| 女生撅嘴 | 女生噘嘴 | `nvshengjuezui` |
| 圆圈M、带圈的M | 圆圈M | `yuanquanm`，末尾 `m` 是字母本身 |
| 天狗面具 | 天狗面具 | `tiangoumianju` |
| 两个爸爸和一儿一女 | 两个爸爸和一儿一女 | `lianggebabaheyieryinv` |

此补充面向全拼；没有把全拼编码当作双拼、五笔或其他方案的可用证据。只匹配完整输入，不做拼音前缀扩展、句中替换或拼写纠正。原 Emoji 名称与其他合理解释继续保留。

## 本轮范围

第 3 阶段收尾新增 28 个可选入口，覆盖严格档补缺中未找到的完整中文名称。其余补缺名称沿用已能找到的宿主候选。以下是首轮 36 个入口的审定记录。

174 个原未找到名称均有逐项决定，归并为 137 个选定入口。复查选定入口时，宿主原本能提供 101 个完整中文候选；36 个仍未找到，才加入这个可选补充。另补 8 个完整中文候选与 Emoji 的关系：酷标志、新品标志、即将到来标志、女生／男生单手摊开、女生／男生噘嘴、尖叫的猫。它们从一般档起生效，句中匹配和严格档权限没有扩大。

家庭、性别、人物方向、信箱开关及旗子状态保留明确描述，不为缩短拼音而合并不同目标。名称选择是逐项语言判断，不是实测词频排行。

源码中的 `data/pinyin_entry_review/` 保存原始 174 条决定、137 条输入，以及生成器和回归所需的精简原生记录。原生记录来自隔离 librime 的候选、预览和提交接口。全量 Lua 覆盖报告可按下方命令重建。

## 验证结果（2026-11-10）

- 原先 52 个目标均已验证可达：17 个复用宿主可输入的自然叫法，35 个使用可选整词补充。第 36 个补充名称是之前为 😊 保留的“害羞的笑脸”。
- 174 条旧名称各有已验证的选定入口，合计 137 个不同名称。137 个候选、137 个预览、137 次仅 Emoji 提交和 137 次原文加 Emoji 提交全部通过。选定叫法见 `data/pinyin_entry_review/reviews.json`。
- 补充的 36 个名称使用音节分隔符输入时，候选、预览及两种提交也全部通过。
- 全量 1,906 项在一般／发散档继续可达；14,010 个查询执行 42,030 次 Lua 调用。修改前已有的 14,002 个查询，三档输出全部不变。
- 此轮历史套件执行 163 项，154 项通过。其余 9 项旧语义断言均在改动前的 HEAD `ccf5d64` 隔离副本中复现。第三阶段的最终验收见[词边界与两档验收](word-boundaries.md)。
- 补充入口开关、英文模式、未命中输入候选顺序和普通空格提交均通过原生检查；最终打包及专项 6 项复跑通过，包括解包后加载可选 translator。

本轮未部署、未写活动配置或用户词库、未提交或发布。

复现生成与本轮检查：

```sh
PYTHONPATH=src .venv/bin/python -m shi_emoji.pinyin_entries
PYTHONPATH=src .venv/bin/python -m shi_emoji.tier_export
PYTHONPATH=src .venv/bin/python -m shi_emoji.reachability \
  --natural-names --output /tmp/shi-emoji-pinyin-entry-repairs
.venv/bin/python scripts/prepare_wanxiang_probe.py \
  --source /path/to/compiled/rime --output /tmp/new-pinyin-probe \
  --zero-key --no-adult --pinyin-entries
PYTHONPATH=src .venv/bin/python scripts/probe_entry_repairs.py \
  --profile /tmp/new-pinyin-probe --input data/pinyin_entry_review/selected_queries.json \
  --both-modes --output /tmp/pinyin-native.json
```

`--output` 的 profile 必须为新目录；历史审定及修复前证据保持原样，避免覆盖。
