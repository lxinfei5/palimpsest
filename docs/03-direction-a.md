# 方向 A 宪章：Agent-native 书稿仓库

**产品名：** Palimpsest · 叠简  
**选定：** 2026-08-12  
**宗旨（要解决什么问题）：** 见 [`00-purpose.md`](./00-purpose.md)。一句话：让长篇小说在跨章、跨会话、跨模型之后，仍然是同一本可审计的书。  
**方向一句话：** 用可以 git、可以换 Agent 的书稿文件夹，作为守住这条宗旨的手段。

主张、宗旨与架构铁则的真源是仓库根目录 [`README.md`](../README.md) 与 [`AGENTS.md`](../AGENTS.md) §0，推理过程以 [`00-purpose.md`](./00-purpose.md) 为准。本文只记录方向选定与范围，不另立一套原则。

---

## 1. 我们做什么

为认真写长篇（或深改写 / 续写）的人，用下列手段守住宗旨（书仍可审计）：

1. 一书一文件夹（`00`–`09`）  
2. 对这份数据可重复执行的指令（ingest → parse → continue / rewrite → review → export）  
3. 给 Coding Agent 的强制规约  

阅读器、ST / EPUB 导出是指令的一种，不是平行产品。文件夹是手段：若它不能让书保持可审计，就只是目录。

**不是：** 对话酒馆、一键万章、绕检测网文工厂、可视化 Codex。

---

## 2. 设计原则（硬）

以根目录 **架构铁则** 六条为准，此处不复制。落地时仍遵守：模型 BYOK / 不锁厂商；不内置版权库与盗站抓取；demo 用原创样例。

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
