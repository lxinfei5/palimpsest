# 二期工作单（并行）

在 MVP 之上补齐方向 A 第二阶段。各模块通过 `palimpsest.plugins.register_commands` 自注册 CLI，**不要改 `cli.py` 主体**，以免并行冲突。

约定：模块提供 `register_cli(subparsers)`。

## P2-A 质量门槛与 Session

- 文件：`src/palimpsest/quality.py`、`tests/test_quality.py`
- 模板：`templates/book/08_sessions/TEMPLATE.md`、必要时补 `09_reviews/`
- 规约：更新 `AGENTS.md` §5.4 / §5.5 / §9（续写/改写验收清单）
- CLI：`palimpsest quality <book-id> [--chapter c004]`
- 检查：front matter（id/kind/source）、字数相对 brief、session 日志是否存在且含 Input/Actions/Open questions

## P2-B 上下文装配与 chunks

- 文件：`src/palimpsest/context.py`、`tests/test_context.py`
- 文档：`docs/05-context.md`（优先级表 1–7）
- CLI：`palimpsest context <book-id> [--chapter c004] [--max-chars N]`
- 行为：按 AGENTS §8 组装一份可粘贴的上下文清单；可选把 `01_sources/normalized` 切成 `01_sources/chunks/`（确定性切片，不调用模型）
- 对 harbor-bell 可生成示例 chunks 或在命令中即时切片

## P2-C 导出 ST + EPUB

- 文件：`src/palimpsest/export/`（`__init__.py` 含 `register_cli`）
- CLI：`palimpsest export st <book-id>`、`palimpsest export epub <book-id> [--volume original|continue|…]`
- ST：世界书 JSON + chara_card_v2 **写作卡**，只读 L2（canon/continuity/prompts），禁止塞原文全文
- EPUB：stdlib 或轻依赖；从 manuscript 分册打包
- 产出目录：`07_export/`
- 测试：`tests/test_export.py`，用 harbor-bell

## P2-D 一致性检查

- 文件：`src/palimpsest/check.py`、`tests/test_check.py`
- CLI：`palimpsest check <book-id> [--volume continue]`
- 规则（启发式即可）：
  1. 正文出现的人名是否都能在 canon 索引/aliases 中解释（漂移）
  2. `open_threads` 中 `must_keep_on_continue` 且 status=open 的线索，最近续写是否至少提及关键词
  3. 角色状态 `as_of_chapter` 是否落后于最新稿
- 退出码：有 warning 仍 0，有 error 为 1

## 共同约束

- Apache-2.0；demo 书保持 CC0
- 不引入盗站抓取、不把聊天当真相源
- 不改 `books/harbor-bell` 原作正文；可追加导出产物或 chunks
- 测试必须过：`pytest -q`
- 中文用户文档，代码与 CLI 英文
