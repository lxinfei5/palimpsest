# 方向 A 宪章：Agent-native 书稿仓库

**产品名：** Palimpsest · 叠简  
**选定：** 2026-08-12  
**一句话：** 把长篇小说做成 Agent 可操作的、可版本化的本地工程。

---

## 1. 我们做什么

为认真写长篇（或深改写 / 续写）的人，提供一套：

1. **一书一沙箱**的目录与 schema  
2. **可重复的任务契约**（ingest → parse → continue / rewrite → review → export）  
3. **Canon / Continuity / Evidence** 三件套，约束长篇一致性  
4. **给 Coding Agent 的强制规约**（如 `AGENTS.md`），使 Cursor / Claude Code / 同类工具成为主生产力  
5. **可选**：最小阅读器、导出 ST 世界书/角色卡、通用 md/epub

**不是：** 又一个对话酒馆、又一个积分制一键万章、又一个绕检测网文工厂。

---

## 2. 设计原则（硬）

| # | 原则 | 含义 |
|---|------|------|
| P1 | 文件即真相源 | 设定与正文以仓库文件为准；聊天可丢 |
| P2 | 一书一沙箱 | 默认禁止跨书串设定 |
| P3 | 信任分层 | L0 原料不可信 → L2 工程真相 → L3 规程最高 |
| P4 | 原作不覆盖 | original 只读；续写/改写/番外分册 |
| P5 | 推断可标记 | canon vs inferred；关键条带 evidence |
| P6 | 任务有契约 | 每个 Agent 任务有明确输入/输出路径 |
| P7 | 模型可替换 | BYOK / 本地；不锁单一厂商 |
| P8 | 合规默认 | 不内置版权库、不内置盗站抓取；demo 用原创样例 |

---

## 3. 目标用户（方向 A 的优先级）

1. **Primary：** 会用 Coding Agent 的作者 / 同人写手 / 世界观构建者  
2. **Secondary：** 愿意「用文件夹写书」的技术向作者  
3. **Non-goal（一期）：** 纯小白所见即所得网文日更用户（可留给未来壳层）

---

## 4. 能力范围

### 4.1 MVP（建议第一刀）

| 模块 | 交付物 |
|------|--------|
| 书脚手架 | `palimpsest new <book-id>` 或等价脚本 |
| Schema | book / character / continuity / volume 最小集合 |
| Agent 规约 | 根级 `AGENTS.md` + 任务短语手册 |
| 样例书 | 短篇原创 demo（CC0），跑通 parse → continue 一章 |
| 阅读 | 只读本地阅读器（可从 novel-lab reader 演化）或 `md` 直读 |
| 文档 | 30 秒上手 + 任务契约说明 |

**MVP 明确不做：** 云同步、协作、可视化 Codex 大编辑器、一键全书生成、移动端、内置付费模型。

### 4.2 第二阶段（仍属方向 A）— 已落地 2026-08-13

- [x] `continue` / `rewrite` 质量门槛与 session 日志标准化（`palimpsest quality`）  
- [x] 上下文装配说明 + chunks（`docs/05-context.md`，`palimpsest context`）  
- [x] 导出 ST 世界书/写作卡与 EPUB（`palimpsest export`）  
- [x] 简单一致性检查（`palimpsest check`）

### 4.3 刻意延后

- 完整 GUI Codex（那是方向 B 的壳）  
- 网文平台投稿工作流  
- 多人实时协作  

---

## 5. 与参考材料的继承关系

| 继承自 novel-lab | 处理 |
|------------------|------|
| 目录流水线 00–09 | 采用并清洗命名，去掉 nsfw 分架硬编码（改为 meta 字段） |
| AGENTS 任务契约 | 重写为 Palimpsest 规约 |
| character evidence schema | 保留精简版 |
| ST compile | 二期可选 |
| 站点定向 ingest | **不继承** |
| 私有书目正文 | **不继承** |

| 继承自 SillyTavern | 处理 |
|--------------------|------|
| 世界书/角色卡格式兼容 | 导出适配器，非运行时依赖 |
| 提示装配理念 | 写入上下文优先级文档 |
| 整站 fork | **不做** |

---

## 6. 技术倾向（暂定，可在实现时调整）

- **存储：** 纯文件（YAML + Markdown）为主；不强制 DB  
- **语言：** 脚手架脚本 Python 或 Node 其一即可；Agent 规约与 schema 语言无关  
- **运行：** 本地 CLI + 可选静态阅读器  
- **LLM：** 用户自备；项目只定义提示与文件契约  

---

## 7. 成功标准（方向 A 是否成立）

若下列成立，则方向 A 跑通：

1. 新用户 10 分钟内用 demo 书看到：canon 角色表 + 续写一章落盘  
2. 换一个 Coding Agent，仅凭仓库内规约能完成同一任务契约  
3. 两本书并行时不会串设定  
4. 仓库可 git 管理，diff 可读  

---

## 8. MVP 落地（2026-08-12）

- [x] 开源许可证：软件 Apache-2.0；demo 书 CC0-1.0  
- [x] 冻结目录 schema（扁平 `books/<id>`，分级进 `content_rating`）  
- [x] `AGENTS.md` + `PHRASES.md` + 样例书 `harbor-bell`  
- [x] CLI：`new` / `list` / `validate` / `serve` / `path`  

实现后仍受本宪章约束，避免范围膨胀。
