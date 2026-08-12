# 导出产物（可选）

编译对外资产到此目录。产物可再生成，勿当作正典。

**只读 L2**：`02_canon/**`、`03_continuity/**`、`06_prompts/**`、`00_meta/book.yaml`。  
**禁止**把 `01_sources` 全文整段打进世界书或角色卡。

## 命令

```bash
palimpsest export st <book-id>
palimpsest export epub <book-id> [--volume original|continue|…]
```

## 产出

| 路径 | 格式 |
|------|------|
| `st/<book-id>-lore.json` | SillyTavern World Info（`entries` 为 uid 映射） |
| `st/<book-id>-writer.json` | `chara_card_v2` 写作卡；`data.extensions.world` = `<book-id>-lore` |
| `epub/<book-id>-<volume>.epub` | 分册 EPUB（去掉章节 YAML front matter） |

世界书规则：S 级角色 `constant: true` 且 `order >= 100`；A/B/C 为 `selective`。文风来自 `06_prompts/system.md` 的一条 constant 条目。角色 `content` 只摘要 yaml 中的 summary / appearance / personality / goals / relationships。
