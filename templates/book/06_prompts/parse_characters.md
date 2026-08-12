# 角色解析提示（Agent 自用）

从规范化正文中抽取角色，写入 `02_canon/characters/`。

## 步骤
1. 第一遍：列出所有人名与别称 → 草稿表
2. 第二遍：按出场权重与剧情功能定 tier（S/A/B/C）
3. S/A 写满 schema；B 可精简；C 进 `_extras.yaml`
4. 每条关键事实尽量附 `evidence.quote`
5. 推断标记 `inferred: true`
6. 更新 `_index.yaml` 与 `_relationships.md`
7. 矛盾写入 `03_continuity/conflicts.md`

## 不要
- 不要把地点名误当人名
- 不要合并明显不同的人，除非原文确认是化名
- 不要为了「完整」编造外貌/年龄
