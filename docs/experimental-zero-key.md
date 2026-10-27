# 实验功能：0 键上屏 Emoji

在当前高亮的完整中文候选有主库联想时，候选旁显示 `〔0 → 🦐 🍤〕`；按主键区 `0` 只上屏 Emoji。空格和 1～6 仍选原文；没有联想、诗Emoji关闭或英文模式时，`0` 交还原输入方案处理。

在已有中文方案的 `*.custom.yaml` 的 `patch` 下加入：

```yaml
  "menu/page_size": 6
  "shi_emoji/candidate_slot": false
  "shi_emoji/zero_key": true
```

重新部署后生效。该模式不新增候选行；高亮换到同音词时，`0` 对应的 Emoji 也跟着换。万象的 `7` 恢复原用途，但高亮词有 Emoji 时，`0` 不再输入声调，而是提交 Emoji；没有 Emoji 时仍按万象原规则处理。旧的 ⌥+回车仍可提交「原文 + Emoji」，不作为此模式的主要操作。

不要与[第 7 项候选槽实验](experimental-candidate-slot.md)同时启用。关闭此实验时，删除 `shi_emoji/zero_key`，并按原方案需要恢复页面大小，重新部署。
