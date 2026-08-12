# 对 Agent 怎么说（复制即用）

工作区根目录：本仓库。先读 `AGENTS.md`。

---

## 新建 + 解析

```text
工作区：Palimpsest 仓库根目录
请严格按 AGENTS.md 执行。

1. palimpsest new <id> --title "<书名>"
2. 将原文从 <本地路径> 执行 ingest
3. parse-characters + parse-world
4. 输出 S/A 角色总表，并列出待我确认的低置信项
```

## 只解析角色

```text
解析 books/<id> 的角色。
按 schemas/character.schema.yaml。
S/A 独立 yaml，C 进 _extras，更新 _index 与 relationships。
```

## 续写一章

```text
续写 books/<id>。
先读 continue_brief（没有就根据我说的写一份），
再写 05_manuscript/volumes/continue/ 下一章。
遵守 canon 与 continuity，写完更新 character_states 与 open_threads。
```

## 改写指定章

```text
按 books/<id>/04_outline/rewrite_brief.md 改写。
产出到 05_manuscript/volumes/rewrite/，不要覆盖 original。
```

## 对照（只读）

```text
对照 books/<id-a> 与 books/<id-b>，只读不写。
```
