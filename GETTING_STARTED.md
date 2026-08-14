# 30 秒上手

先读根目录 [`README.md`](./README.md) 的主张与架构铁则。下面只讲怎么跑。

```bash
cd palimpsest
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 看样例书
.venv/bin/palimpsest list
.venv/bin/palimpsest validate harbor-bell
.venv/bin/palimpsest quality harbor-bell
.venv/bin/palimpsest check harbor-bell
.venv/bin/palimpsest context harbor-bell --chapter c004 --max-chars 4000
.venv/bin/palimpsest export st harbor-bell
.venv/bin/palimpsest export epub harbor-bell --volume original

# 本地阅读
.venv/bin/palimpsest serve
# 打开 http://127.0.0.1:8765/
```

样例书 `books/harbor-bell`（《港铃》）是原创短篇（CC0）：三章原作 + 一章续写，canon / continuity 已填好。

## 新建自己的书

```bash
.venv/bin/palimpsest new my-xianxia --title "我的仙侠"
# 把你拥有权利的 txt/md 放进 books/my-xianxia/01_sources/raw/
```

然后对 Coding Agent 说（见 `PHRASES.md`）：

```text
解析 books/my-xianxia，按 AGENTS.md 执行 ingest + parse-characters + parse-world。
```

## 目录流水线

| 路径 | 含义 |
|------|------|
| `00_meta/` | 书目元数据 |
| `01_sources/` | 原文（raw 只读） |
| `02_canon/` | 正典设定 |
| `03_continuity/` | 动态状态与伏笔 |
| `04_outline/` | 大纲 / 任务书 |
| `05_manuscript/` | 正文；续写在 `volumes/` |
| `06_prompts/` | 本书提示词 |
| `07_export/` | 可选导出 |
| `08_sessions/` | Agent 日志 |
| `09_reviews/` | 审校 |

更完整的边界见 `docs/03-direction-a.md`。
