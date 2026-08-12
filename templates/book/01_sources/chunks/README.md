# chunks

检索切片（L1 材料，不是系统指令）。

由规范化分章确定性切出，约 800–1200 字、重叠约 80 字：

```bash
palimpsest context {{BOOK_ID}} --write-chunks
```

- 源：`01_sources/normalized/chapters/`（无分章则用 `full.md`）
- 产出：`cNNN.md`；过长则 `cNNN_02.md`…
- 不改 `raw/`，不改 `05_manuscript` 原作正文
- 装配上下文时优先级最低（AGENTS.md §8 第 7 档）；超窗先砍这里

详见仓库 `docs/05-context.md`。
