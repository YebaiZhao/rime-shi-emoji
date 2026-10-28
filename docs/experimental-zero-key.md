# 实验功能：0 键上屏 Emoji

在当前高亮的完整中文候选有主库联想时，按主键区 `0` 默认上屏「原文 + 空格 + Emoji」，例如 `虾仁 🦐 🍤`，候选旁显示 `〔0 → 原文＋🦐 🍤〕`。在 Ctrl + 反引号选单中切到「仅Emoji」后，同一个 `0` 键只上屏 `🦐 🍤`，提示改为 `〔0 → 🦐 🍤〕`。空格和 1～6 仍选原文；没有联想、诗Emoji关闭或英文模式时，`0` 交还原输入方案处理。

在已有中文方案的 `*.custom.yaml` 的 `patch` 下加入：

```yaml
  "menu/page_size": 6
  "shi_emoji/candidate_slot": false
  "shi_emoji/zero_key": true
```

在同一方案补丁的**现有** `switches/+` 列表末尾追加以下一项，不要新建第二个 `switches/+` 键：

```yaml
    - name: shi_emoji_emoji_only
      states: [原文＋Emoji, 仅Emoji]
```

在 `default.custom.yaml` 的**现有** `switcher/save_options/+` 列表追加 `shi_emoji_emoji_only`，与 `shi_emoji` 总开关一起保存。不要给此开关加 `reset`；未保存过时默认「原文＋Emoji」，之后记住各账号在选单中的选择。

重新部署并重载后，选单会多一项输出方式。选单文字显示**当前状态**：初次看到「原文＋Emoji」，点它才切到「仅Emoji」；再点「仅Emoji」切回来。该模式不新增候选行；高亮换到同音词时，`0` 的内容也跟着换。万象的 `7` 恢复原用途，但高亮词有 Emoji 时，`0` 不再输入声调，而是提交所选输出；没有 Emoji 时仍按万象原规则处理。⌥+回车始终提交「原文 + Emoji」，不受选单影响。

不要与[第 7 项候选槽实验](experimental-candidate-slot.md)同时启用。关闭此实验时，删除 `shi_emoji/zero_key`、对应的 `shi_emoji_emoji_only` 选单项及保存项，并按原方案需要恢复页面大小，重新部署。
