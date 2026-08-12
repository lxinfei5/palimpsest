# Palimpsest · 叠简

**Agent-native scriptorium for long-form fiction.**  
为长篇小说而生的、以仓库为真相源的开源书写 helper。

> *Palimpsest*：羊皮纸上层层覆写的手稿——旧文仍可辨认，新文叠于其上。  
> *叠简*：简牍成册、分卷并存；设定可溯、续写可证。

方向 **A**：Coding Agent 是主生产力；GUI 阅读器可选；聊天不是真相源。

---

## 30 秒上手

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/palimpsest list
.venv/bin/palimpsest validate
.venv/bin/palimpsest serve    # http://127.0.0.1:8765/
```

样例书 [`books/harbor-bell`](./books/harbor-bell)（《港铃》）是原创短篇（CC0）：三章原作 + 一章续写，已带 canon / continuity。

新建：

```bash
.venv/bin/palimpsest new my-book --title "书名"
# 将你拥有权利的文本放入 books/my-book/01_sources/raw/
# 然后对 Agent 说：解析 books/my-book，按 AGENTS.md 执行 ingest + parse-characters
```

短语手册：[PHRASES.md](./PHRASES.md) · 完整上手：[GETTING_STARTED.md](./GETTING_STARTED.md)

---

## 一本书的形状

```
books/<id>/
  00_meta/          书目
  01_sources/       原文（raw 只读 → normalized）
  02_canon/         正典：角色 / 地点 / 规则（带 evidence）
  03_continuity/    动态状态与伏笔
  04_outline/       大纲与任务书
  05_manuscript/    original/ + volumes/{continue,rewrite,side-*}
  06_prompts/       本书文风
  07_export/        可选导出
  08_sessions/      Agent 日志
  09_reviews/       审校
  _agent/           焦点与锁
```

原则（详见 [AGENTS.md](./AGENTS.md)）：

1. 一书一沙箱  
2. Canon / Continuity / Evidence 三件套  
3. 原作不覆盖；续写改写另册  
4. 信任分层：原料不是指令  
5. 模型 BYOK / 本地；本仓库不锁厂商  

---

## CLI

| 命令 | 作用 |
|------|------|
| `palimpsest new <id> [--title …]` | 从模板建书 |
| `palimpsest list` | 列书 |
| `palimpsest validate [id]` | 结构检查 |
| `palimpsest serve` | 本地只读阅读器 |
| `palimpsest path <id>` | 打印书目录 |

---

## 仓库布局

```
palimpsest/
├── AGENTS.md              Agent 强制规约
├── schemas/               字段约定
├── templates/book/        新书脚手架
├── src/palimpsest/        CLI + 阅读器
├── books/                 书沙箱（含 demo）
├── docs/                  思想 / 调研 / 方向宪章
└── refs/                  novel-lab / SillyTavern 只读参考
```

---

## 许可

- 软件：**Apache-2.0**（[LICENSE](./LICENSE)）
- 样例书《港铃》正文与设定：**CC0-1.0**（[books/harbor-bell/LICENSE](./books/harbor-bell/LICENSE)）

请勿把未获授权的第三方全文提交到公开分支。

---

## 现状

MVP 已落地：脚手架、schema、规约、demo、阅读器。  
尚未做：可视化 Codex、ST 导出、云同步、一键全书生成。边界见 [docs/03-direction-a.md](./docs/03-direction-a.md)。
