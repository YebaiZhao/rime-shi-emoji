# 架构与构建

## 运行时职责

| 文件 | 职责 |
|---|---|
| `processor.lua` | 对高亮且有匹配的完整中文候选，处理 ⌥+回车／⌃⌥+回车；不接管 Tab 或普通输入 |
| `filter.lua` | 默认透传原候选，只给当前高亮项追加主库／重口预览；可选候选槽模式下，在页末插入随高亮变化、只提交 Emoji 的候选 |
| `matcher.lua` | 两棵 trie：词组检索、完整名词保护；局部否定标记 |
| `compose.lua` | 最多三个不重叠、不同概念，按原文顺序组合；单概念最多两个表情 |
| `variants.lua` | 性别/肤色偏好与明确性别表达保护 |
| `data.lua` | 主词库与保护词，离线生成 |
| `variant_data.lua` | 固定 Unicode 目录中确实存在的变体，离线生成 |
| `adult.lua` | 默认关闭的重口联想库，首次开启查询时加载；文件名保留以兼容既有配置 |

主开关关闭或英文模式直接透传；开启且发生查询后才建立索引，模块内复用。关闭不保证立刻回收索引内存。插件不运行 shell、网络请求、后台进程或模型，不采集输入日志；宿主能力及其日志策略另计。

默认安装不增加候选行，也不改变页面大小。可选的[数字候选槽](experimental-candidate-slot.md)会改变页面大小与 `7` 键用途；仅槽位提交 Emoji，原候选仍按宿主规则上屏。

当前是有限词典 + 子串检索 + 完整词保护，不是完整分词或语义解析。否定基于分句和四字前文窗口。候选文字由宿主提供，多义词和识别错误仍会造成错误。设计与历史记录见 [匹配细节](phrase-mode.md)、[逐词决策](mapping-resolution.md)、[质量边界](evaluation.md)。

## 不运行模型也能构建发布包

Python 3.10+。仓库包含已生成的数据和完整来源记录，以下命令使用标准库：

```sh
PYTHONPATH=src python3 -m shi_emoji.export
PYTHONPATH=src python3 -m shi_emoji.preferences
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/package_runtime.py
```

输出 `dist/rime-shi-emoji-runtime.zip`，附文件摘要；相同构建环境、相同文件内容得到相同 ZIP。不同 Python/zlib 版本不承诺压缩字节完全一致。模型权重、个人 profile、完整原始预测和 Python 均不进入运行时 ZIP。

## 重新生成词法目录与保护词

首次获取固定数据需要网络，随后可用缓存离线生成：

```sh
PYTHONPATH=src python3 -m shi_emoji.sources
PYTHONPATH=src python3 -m shi_emoji.coverage --fetch --check
PYTHONPATH=src python3 -m shi_emoji.wordguards
PYTHONPATH=src python3 -m shi_emoji.export
PYTHONPATH=src python3 -m shi_emoji.preferences
```

`sources` 会刷新离线模型的查询/目录输入；若之后重用旧预测，哈希改变会阻止 `--reuse`，需要明确重跑推理。生成 Lua 不需要重新推理。数据哈希分别记录在 `source_manifest.json`、`lexical_phrases.json`、`word_guards.json` 和模型审核记录中。

## 测试分层

标准库测试可检查数据、导出、打包；Lua 测试需要系统 `liblua5.4` 或本机 Squirrel 库。CI 配置安装系统 Lua，原生 Rime 测试在 Linux 上仍会跳过。

本机原生检查需要 Squirrel、已编译中文字典及 PyYAML（可安装项目 `test` extra）。先新建一次性 profile：

```sh
python3 scripts/prepare_wanxiang_probe.py --source /path/to/compiled/rime --output dist/release-probe
python3 scripts/check_release.py --profile dist/release-probe
```

`--source` 只读引用静态资源；`--output` 必须新建，绝不能用活动用户目录。严格检查拒绝没有隔离标记的 profile，出现任何跳过测试即失败。直接 `unittest` 允许报告跳过项，不等于完整发布验证。

## 离线模型建库（可选）

`pip install -e '.[build]'` 提供建库工具；固定模型为 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`，revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`。需先将该版本权重准备到 Hugging Face 本地缓存，生成器使用 `local_files_only=True`；不替用户自动下载或安装模型。

历史模型的输入、原始预测、审核记录保留在源码仓库。其复现环境没有完整依赖锁，不承诺在所有环境重新推理会得到逐字节相同结果；运行时发布包可从提交的产物构建。参见 [历史模型审核记录](model-supervision.md)。不要为改写历史文档而修改已签核摘要，也不要把“记录了审核哈希”描述为数字签名。

早期独立拼音词典构建器和实验 schema 仍保留在源码中，不属于当前用户安装路径。
