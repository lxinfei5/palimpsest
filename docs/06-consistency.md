# 一致性检查（P2-D）

CLI：`palimpsest check <book-id> [--volume continue]`

启发式三条，不调用模型。

| 规则 | 做什么 | 级别 |
|------|--------|------|
| name-drift | 正文里像人名的词能否被 `02_canon` 解释 | **error** |
| open-threads | `must_keep_on_continue` 且 `status: open` 的线索，最近续写（或指定分册最新章）是否点到标题/摘要里的关键词 | warning |
| stale-states | `character_states.yaml` 的 `as_of_chapter` 是否落后于扫描范围内最新章 | warning |

退出码：仅 warning → `0`；有 error → `1`。

## 人名漂移

1. 从 `02_canon/characters/_index.yaml`、各角色卡、`_extras.yaml` 收集 `name` / `aliases`。
2. 地点、物品、势力、术语、规则的 `name` / `aliases` 一并加入允许表（所以「灰屿」「灯塔」「鹿回头」「铜铃」不会误报）。
3. 扫描指定分册，或默认全部 `05_manuscript` 分册。
4. 只把**像完整人名**的记号当问题：
   - 三字、百家姓开头，或四字复姓（欧阳 / 司马…）+ 名；名字里不含虚词、趋向/言说动词；
   - 或拉丁文 `First Last`。
5. 二字词（如「朱砂」）以及「边角磨圆」这类单姓四字短语默认不报。

因此，正文里冒出未入典的「赵铁柱」这类完整汉名 → **error**。路人若只写「那汉子」则不会触发。

## 未收束线索

只检查 `must_keep_on_continue: true` 且仍 `open` 的条目。未指定 `--volume` 时看 **continue** 分册最新章；指定了则看该分册最新章。标题、引号短语、摘要里的专名/二字以上实词，命中任一即算提及。漏了只警告，不判失败。

## 过期状态

`as_of_chapter` 的排序键小于范围内最新 `cNNN` / `rNNN` / `sNNN` 时警告。状态超前（续写已更新、却在扫原作分册）不警告。
