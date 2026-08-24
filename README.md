# Palimpsest · 叠简

> **让长篇小说在跨章、跨会话、跨模型之后，仍然是同一本可审计的书。**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Live Demo](https://img.shields.io/badge/Live%20Demo-lxinfei5.win%2Fpalimpsest-8A2BE2.svg?logo=cloudflare)](https://lxinfei5.win/palimpsest/)

---

## 🌐 在线实时体验 (Live Demo)

无需本地安装，直接在浏览器中体验 Palimpsest 全功能小说工程工作台：

🔗 **[https://lxinfei5.win/palimpsest/](https://lxinfei5.win/palimpsest/)**

> 💡 **演示亮点**：
> - 📖 **正文分册阅读**：原作 (original) / 续写 (continue) 物理分卷隔离，夜间 / 日间 / 古籍羊皮纸 (Parchment) 沉浸排版。
> - 👥 **正典百科与证据链**：S/A/B 角色卡与**原文精确短引（Evidence quote & ref）**。
> - 🧭 **状态与伏笔监控**：角色此刻动态状态矩阵 (`character_states`) 与未收束伏笔追踪 (`open_threads`)。
> - 🛡️ **一键门禁审计**：在线运行 `Quality` 续写门禁、`Check` 静态防人名漂移扫描、`Validate` 目录合规校验。
> - ⚡ **上下文装配与导出**：滑块动态设定 Token/字符预算装配 Prompt，一键下载 EPUB 与 SillyTavern 酒馆世界书。

---

## 📖 什么是 Palimpsest？

**Palimpsest（重写本 / 叠简）** 指古代羊皮纸上擦拭后重新书写、但底层墨迹依然可辨的重写文本。

在 AI 辅助长篇创作的世界里，我们缺少的从来不是“写出下一段话”的模型能力，而是**在关闭聊天窗口之后依然留存的那本书**。

### 问题空间的勘测（Why Palimpsest?）

长篇小说在引入 AI 创作时，往往会在写到数万字后陷入失控，其根本原因在于传统工具忽视了**“书本身是一个需要工程化管理的数据对象”**：

1. **上下文遗忘与漂移**：聊天记忆随着会话结束而清空，换个模型或跨过几十万字后，AI 开始胡乱捏造设定。
2. **正典（Canon）与状态（Continuity）混杂**：历史已确立的事实与“此刻这一章的状态”搅在一起，写完新章节后无人回写状态，导致下一章对着过期的旧卡生成。
3. **原作被覆盖与黑盒锁定**：续写和改写直接覆写原稿，无法追溯；商业写作软件将设定锁在私有云数据库中，无法 Git 协作，无法本地 Diff，换工具即作废。
4. **一键生成器的虚假繁荣**：一口气连写百章的脚本无法保证长篇前后的逻辑一致性与人物弧光。

### 我们的第一性原理

> **书是一份耐久、可版本化、带证据链的数据对象，而不是一次性的聊天记录或封闭的 SaaS 数据库。**

Palimpsest 把长篇小说当成一个 **Git 仓库** 来管理，并为 **Coding Agent**（如 Claude Code, Cursor, Windsurf 等）提供一套确定性的操作契约：

- 📁 **一书一文件夹**：每本书独立存放在 `books/<book-id>/`（`00`–`09` 目录），文件夹是**唯一真相源**。
- 🧊 **正典冻结，状态可变，原作不覆盖**：关键设定强制携带原文证据短摘录（Evidence）；此刻状态动态追踪；续写与改写分册独立落盘。
- 🛡️ **确定性归代码，创造力归模型**：文件 I/O、格式校验与质量门禁由本地 Python CLI 严格把控，不浪费模型算力；文本理解、世界观抽取与正文创作由 Agent 执行。
- 🔒 **防正文注入与一书一沙箱**：外部原文与网页均为不可信材料（L0/L1），正文中的提示词注入会被代码层与规约严格过滤；多书之间默认绝对隔离。

---

## 🗂️ 单本书的标准结构（00–09 规范）

在 `books/<book-id>/` 目录下，所有数据被清晰地解耦为 10 个层级：

```text
books/<book-id>/
├── 00_meta/          # 书目元数据（book.yaml）
├── 01_sources/       # 原文材料（raw 只读原稿 / normalized 标准分章 / chunks 检索切片）
├── 02_canon/         # 正典设定（人物/地理/势力/规则/时间线，带原文证据）
├── 03_continuity/    # 动态状态（人物当前状态/未解伏笔 open_threads/冲突记录）
├── 04_outline/       # 纲要与任务书（分卷大纲、continue_brief、rewrite_brief）
├── 05_manuscript/    # 正文手稿（original 原作 / volumes 分卷续写与改写）
├── 06_prompts/       # 本书专属 Prompt 与文风约定（system.md）
├── 07_export/        # 衍生导出物（分卷 EPUB、SillyTavern 世界书等）
├── 08_sessions/      # Agent 会话审计日志（Input / Actions / Open questions）
├── 09_reviews/       # 审校与质量清单（quality_checklist.md）
└── _agent/           # Agent 当前焦点与状态锁（STATE.md）
```

---

## 🚀 快速上手（Quick Start）

### 1. 环境准备与安装

需要 Python 3.10+ 环境：

```bash
# 克隆仓库
git clone https://github.com/lxinfei5/palimpsest.git
cd palimpsest

# 创建虚拟环境并安装核心依赖
python3 -m venv .venv
source .venv/bin/activate  # Windows 用户使用 .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. 体验内置样例书《港铃》

项目中自带了一本完整的短篇小说样例 [`books/harbor-bell`](./books/harbor-bell)（CC0 许可，包含三章原作 + 一章续写及完整正典）：

```bash
# 查看当前所有书目
palimpsest list

# 检查书籍目录结构与 Schema 合规性
palimpsest validate harbor-bell

# 运行续写质量门禁检查（检查章节元数据、字数偏离度与 session 记录）
palimpsest quality harbor-bell

# 运行一致性静态检查（检测实体提及与伏笔状态）
palimpsest check harbor-bell

# 为特定章节按优先级装配上下文
palimpsest context harbor-bell --chapter c004 --max-chars 4000

# 启动本地可视化工作台（Web GUI，自动打开浏览器）
palimpsest gui
# 或使用阅读服务：palimpsest serve
# 浏览器访问 http://127.0.0.1:8765/
```

### 3. 创建你的第一本书

只需两步即可建立属于你自己的小说工程：

```bash
# 1. 初始化新书工程
palimpsest new my-book --title "我的第一本小说"

# 2. 将你拥有版权的原始素材（txt 或 md 格式）放入 raw 目录
cp /path/to/your/raw.txt books/my-book/01_sources/raw/
```

### 4. 唤起 Coding Agent 协作

在你的 Agent 界面（如 Claude Code / Cursor / Windsurf / Antigravity）中，直接向 Agent 发送指令：

```text
请阅读 AGENTS.md，对 books/my-book 执行 ingest，随后进行 parse-characters 与 parse-world。
```

Agent 会自动按照 [AGENTS.md](./AGENTS.md) 的任务契约完成原始材料的清洗规范化、抽取 S/A/B 级角色卡（附带原文证据引用）、梳理势力与世界观规则，并生成会话日志。

---

## 🛠️ 开发者指南（Developer Guide）

如果你希望为 Palimpsest 贡献代码、扩展命令或对接自定义工作流，请参考以下指引。

### 1. 架构核心与模块分工

代码仓库位于 [`src/palimpsest/`](./src/palimpsest/)，核心逻辑分为以下几层：

| 模块 | 核心职责 |
|---|---|
| [`cli.py`](./src/palimpsest/cli.py) | 统一的 Click 命令行入口与参数解析。 |
| [`books.py`](./src/palimpsest/books.py) & [`paths.py`](./src/palimpsest/paths.py) | 书籍发现、模板脚手架生成、规范路径计算。 |
| [`validate.py`](./src/palimpsest/validate.py) | 基于 YAML Schema 对 `00`–`09` 各目录结构和元数据的静态合规性校验。 |
| [`quality.py`](./src/palimpsest/quality.py) | 续写与改写的质量门禁（强制要求 `front matter` 标识、字数偏差预警、审计日志匹配）。 |
| [`check.py`](./src/palimpsest/check.py) | 文本一致性检测器（实体出现频次、别名识别、未闭合伏笔告警）。 |
| [`context.py`](./src/palimpsest/context.py) | 动态上下文组装器（严格按照 Prompt -> Brief -> 角色卡/状态 -> 规则 -> 近文 优先级裁剪拼接）。 |
| [`export/`](./src/palimpsest/export/) | 衍生导出模块（`epub.py` 生成标准电子书，`st.py` 导出 SillyTavern 世界书）。 |
| [`reader/`](./src/palimpsest/reader/) | 基于标准库的轻量只读 HTTP 服务与前端界面。 |
| [`plugins.py`](./src/palimpsest/plugins.py) | 钩子与插件扩展机制。 |

### 2. 运行自动化测试

项目使用 `pytest` 编写了完整的单元测试与集成测试：

```bash
# 运行全部测试
pytest

# 运行特定模块测试
pytest tests/test_quality.py -v
```

### 3. 核心扩展点

- **添加自定义校验规则**：可在 [`src/palimpsest/check.py`](./src/palimpsest/check.py) 中增加新的文本一致性静态分析逻辑（如时间线跳跃检测、阵营冲突检测）。
- **新增导出格式**：在 [`src/palimpsest/export/`](./src/palimpsest/export/) 下实现新的导出生成器，并在 [`cli.py`](./src/palimpsest/cli.py) 的 `export` 命令组中注册子命令。
- **自定义 Schema**：在 [`schemas/`](./schemas/) 目录下维护各实体的 YAML Schema，修改后更新 `validate.py`。

---

## 🌐 生产与 Demo 部署指南（以 lxinfei5.win + Cloudflare 为例）

Palimpsest Web 工作台采用零额外外部重型依赖设计，后端仅依赖 Python 3.10+ 标准库与 pyyaml，可快速安全部署为在线演示站点。

### 1. 安全基线原则

- 🔒 **永远只监听本地回环**：`palimpsest serve` 默认仅监听 `127.0.0.1:8765`，**绝不可直接暴露原生 HTTP 端口到公网**。
- 🛡️ **反向代理与 Cloudflare WAF**：前端由 Nginx / Caddy 进行反向代理，并通过 Cloudflare CDN 代理回源，启用 SSL/TLS、防 DDoS 与防扫描。
- 👤 **最小权限运行**：使用非 root 专用用户（如 `palimpsest` 或容器隔离环境）运行应用。

---

### 2. 方式 A：Docker Compose 极简一键部署（推荐）

仓库已内置生产就绪的 [`Dockerfile`](./Dockerfile) 与 [`docker-compose.yml`](./docker-compose.yml)：

```bash
# 1. 在服务器上克隆仓库
git clone https://github.com/lxinfei5/palimpsest.git
cd palimpsest

# 2. 启动容器（自动构建、仅绑定本地 127.0.0.1:8765）
docker compose up -d

# 3. 查看运行状态与日志
docker compose ps
docker compose logs -f
```

---

### 3. 方式 B：Linux 原生 Systemd 服务部署

如果不使用 Docker，可直接通过 systemd 管理常驻进程：

```bash
# 1. 准备运行环境
git clone https://github.com/lxinfei5/palimpsest.git /home/ubuntu/palimpsest
cd /home/ubuntu/palimpsest
python3 -m venv .venv
.venv/bin/pip install -e .

# 2. 安装 systemd 服务（参考 deploy/palimpsest.service）
sudo cp deploy/palimpsest.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now palimpsest

# 3. 检查服务运行状态
sudo systemctl status palimpsest
```

---

### 4. 反向代理配置（以 Nginx 为例）

将 [`deploy/nginx-lxinfei5.conf`](./deploy/nginx-lxinfei5.conf) 部署至服务器：

```bash
# 1. 复制站点配置
sudo cp deploy/nginx-lxinfei5.conf /etc/nginx/sites-available/lxinfei5.win
sudo ln -s /etc/nginx/sites-available/lxinfei5.win /etc/nginx/sites-enabled/

# 2. 测试配置并重载
sudo nginx -t
sudo systemctl reload nginx
```

并在 **Cloudflare 控制台** 中：
- 将 `lxinfei5.win` 的 DNS 解析记录开启橙色云朵（**Proxied** 代理模式）。
- 在 **SSL/TLS** 设置中选择 **Flexible** 或 **Full** 模式。
- 开启 **Always Use HTTPS** 与 **HTTP/2** 支持。

---

## ⚖️ 生态位与能力对照

| 维度 | Palimpsest 叠简 | Sudowrite / Novelcrafter | 开源一键生成器 | SillyTavern 酒馆 |
|---|:---:|:---:|:---:|:---:|
| **数据归属** | ✅ 本地文件，可 Git、可 Diff | ❌ 锁在厂商云端数据库 | ⚠️ 散落在脚本输出目录 | ⚠️ 浏览器 IndexedDB / 散落文件 |
| **正典与状态隔离** | ✅ 物理分家，关键设定带证据 | ⚠️ 部分支持（易过期） | ❌ 无分层，越写越漂 | ❌ 聊天与设定杂糅 |
| **原作保护** | ✅ 原作冻结，续写/改写另册 | ❌ 直接覆盖原稿 | ❌ 一次性输出 | — |
| **跨模型与 Agent** | ✅ 规约通用，随时换模型/Agent | ❌ 绑定厂商界面与订阅 | ⚠️ 通常绑定特定 API | ❌ 换会话即丢失上下文 |
| **确定性质量门禁** | ✅ 本地代码检查，不耗 Token | ❌ 无 | ❌ 无 | ❌ 无 |
| **目标场景** | 严肃长篇、长线版本化创作 | 商业网文辅助当场润色 | 批量洗稿/粗制烂造 | 角色扮演与聊天互动 |

---

## 📚 延伸阅读与文档矩阵

- 🎯 **[docs/00-purpose.md](./docs/00-purpose.md)**：深入探讨为什么“书是数据对象”的第一性原理与拒绝清单。
- 📜 **[AGENTS.md](./AGENTS.md)**：面向 Coding Agent 的最高行动规约与任务契约。
- ⚡ **[GETTING_STARTED.md](./GETTING_STARTED.md)**：30 秒简明命令速查表。
- 💬 **[PHRASES.md](./PHRASES.md)**：与 Agent 协作时的高效提示词模版。

---

## 📄 许可证 (License)

- 本仓库核心代码采用 **[Apache-2.0](./LICENSE)** 许可证开源。
- 样例书《港铃》（[`books/harbor-bell`](./books/harbor-bell)）采用 **[CC0-1.0](./books/harbor-bell/LICENSE)**（公有领域贡献）。
