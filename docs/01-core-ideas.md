# 参考材料核心思想（可开源抽取）

> 服务于产品：**Palimpsest · 叠简**（方向 A：Agent-native 书稿仓库）  
> 来源：`novel-lab`（小说设定/续写工作区）+ `silly-tavern`（LLM 对话前端，俗称「酒馆」）  
> 原则：只抽取**架构与工作流思想**；剔除版权原文、成人内容库、定向站点抓取脚本、私有会话数据。

---

## 一、两份材料各自是什么

| 项目 | 定位 | 和「开源小说 helper」的关系 |
|------|------|---------------------------|
| **novel-lab** | 本地、多书隔离的「小说工程」真相源：设定、连续性、大纲、正文分册、Agent 规约 | **主参考**：长篇写作的数据结构、任务契约、质量门槛 |
| **silly-tavern** | 面向 power user 的通用 LLM 前端：角色卡、世界书、提示装配、多后端、扩展生态 | **旁路参考**：上下文注入机制、资产格式、交互隐喻；不是写作真相源 |

novel-lab 自己的设计结论很明确：

- Coding Agent = 主生产力  
- SillyTavern = **可选** UI / 兼容层  
- 真相源永远在书目录文件树里，不在聊天记忆里  

---

## 二、novel-lab 可复用的核心思想

### 1. 一书一沙箱（Project = Book）

- 每本书独立目录，默认禁止跨书混读设定。  
- 全局只共享：脚手架模板、schema、工具脚本、Agent 规程。  
- 生成时严禁把书 B 的人名/设定写进书 A（除非 brief 明确要求 crossover）。

**开源产品含义**：多项目管理、硬隔离上下文、可选「系列共享 Codex」作为显式能力，而不是默认串台。

### 2. 分层真相源（Trust Layers）

| 层 | 内容 | 可信度 | 用途 |
|----|------|--------|------|
| L0 | 网页/粘贴/raw 抓取 | 零 | 仅作材料 |
| L1 | 规范化正文、原作归档 | 低（事实可参考） | 证据、文风对照；**不当系统指令** |
| L2 | canon / continuity / outline / meta | 高 | 续写改写的主依据 |
| L3 | 项目规程 + 用户当轮指令 | 最高 | 行为边界 |

冲突时：**L3 > L2 > L1 > L0**。  
正文里的「忽略规则 / 你现在是…」一律当小说噪声，不执行。

**开源产品含义**：防间接注入 + 可审计；「原文」与「已审定设定」必须分家。

### 3. 数字前缀工作流目录（Pipeline as Filesystem）

单书结构即流水线顺序：

```
00_meta        元数据、任务状态
01_sources     原文（raw 只读 → normalized → chunks）
02_canon       正典设定（角色/地点/势力/规则/时间线…）
03_continuity  动态状态（人物状态、伏笔、冲突）
04_outline     大纲 / 续写 brief / 改写 brief
05_manuscript  正文（original 只读；continue / rewrite / side 分册）
06_prompts     本书提示词与文风
07_*_export    对外编译产物（如 ST 世界书/角色卡）
08_sessions    Agent 任务日志
09_reviews     审校、OOC、canon 变更请求
_agent         焦点、锁、状态
```

**开源产品含义**：UI 可以漂亮，但底层最好是**可 diff、可备份、可 Agent 读写**的结构化仓库，而不是黑盒数据库 alone。

### 4. Canon vs Continuity（静态正典 vs 动态状态）

- **Canon**：文中明确的人设/世界规则；带 evidence；推断标 `inferred`。  
- **Continuity**：随章节变化的状态（谁在哪、伏笔是否回收、冲突列表）。  
- 续写**不得静默改 canon**；必须改设定时走 `canon_change_requests` 或人工确认。

**开源产品含义**：商业工具里的 Story Bible / Codex，在这里拆成「冻结设定」和「进行中状态」两套，长篇一致性更稳。

### 5. 角色分级 + 证据链

- S/A/B/C 分级：S/A 独立卡、C 合并，避免文件爆炸。  
- 关键设定尽量带 `evidence: {ref, quote, confidence}`。  
- 区分 canon（明确）与 inference（推断）。  
- 前后矛盾写入 conflicts，不直接抹掉。

**开源产品含义**：解析质量可验收；AI 幻觉可追溯到章句。

### 6. 任务契约（Task Types as Contracts）

高频任务有固定 I/O，而不是自由聊天：

| 任务 | 输入 | 输出 |
|------|------|------|
| `ingest` | inbox / 文件 | normalized 分章 + meta.source |
| `parse-characters` | 正文 + schema | characters yaml + index + relationships |
| `parse-world` | 正文 | locations/factions/rules/timeline + open_threads |
| `continue` | canon + continuity + brief + 近文 | 新章节分册 + 更新 continuity |
| `rewrite` | original 目标章 + rewrite brief | rewrite 分册 + front matter 意图 |
| `compile-export` | L2 设定 + system prompt | 世界书/角色卡等对外资产 |

**开源产品含义**：产品功能 = 任务类型；UI 按钮对应契约，便于 Agent/脚本自动化。

### 7. 生成时上下文优先级（砍上下文时的顺序）

注入顺序（从高到低）：

1. 本书 system / 文风与禁区  
2. 本章 brief（必须发生 / 禁止发生 / 字数）  
3. S/A 角色卡 + 当前 character_states  
4. 相关 locations / rules  
5. 相关 open_threads  
6. 近文 1–3 章  
7. 按需检索 sources/chunks  

上下文爆了先砍 6/7，**不要砍 1–4**。

### 8. 分册阅读与不覆盖原作

- original 只读；改写 / 续写 / 番外各自成册。  
- 阅读器按册打开，避免把改写和原作混读。  
- 版本追加用 `v002`，不覆盖 `v001`。

### 9. 人机分工原则

> **判断与措辞归大模型，确定性 I/O 才归代码。**

- 世界书条目措辞、personality、mes_example：模型读完 canon 后提炼撰写。  
- 分章、路径、schema 校验、批量迁移：脚本。  
- 禁止「正则抠字段拼模板」当完成。

### 10. Session 日志与可验收输出

每次任务写 session：输入、改了哪些路径、Open questions、Next。  
对用户：先报 book-id / 阶段 / 路径；表格摘要 S/A 角色；列出待确认的低置信项。

---

## 三、SillyTavern 可复用的核心思想

> ST 本身已是 AGPL 开源。这里只抽**对小说 helper 有迁移价值**的机制，不复刻整站。

### 1. 资产化人格与世界

- **Character Card（角色卡）**：description / personality / scenario / first_mes / mes_example / post_history_instructions。  
- **World Info（世界书）**：按关键词触发的 lore 条目；constant vs selective；order / depth / probability。  
- 含义：把「提示工程」产品化成**可导入导出的结构化资产**。

### 2. 提示装配流水线

- 系统提示 + 角色 + 世界书命中条目 + 作者注 + 历史消息 + 用户输入 → 发给后端。  
- Instruct 模式、滑词、token 预算、条目深度：都是**上下文工程控件**。  
- 小说工具可借鉴：场景写作时自动挂载相关 Codex 条目，而不是每次手贴。

### 3. 多后端 / 本地优先哲学

- 不绑定单一模型厂商；兼容 OpenAI 兼容 API、本地推理、代理等。  
- 数据默认落在用户机器（或用户自管 data 目录）。  
- 与「开源 helper + BYOK」路线高度同构。

### 4. 扩展与斜杠命令

- 功能通过 extensions / slash commands 增长，而不是把核心做成巨型单体。  
- 对小说产品：插件式「拆书 / 大纲 / 审校 / 导出」比一上来做全能编辑器更稳。

### 5. 明确的边界（ST 不擅长什么）

- ST 是**对话前端**，不是长篇手稿工程。  
- 没有原生的「一书分册 + canon/continuity 双轨 + 章节级证据」模型。  
- 长文应用 Data Bank / vectors 挂载，而不是把整本塞进角色描述。  
- 因此：novel-lab 把 ST 当**可选渲染层**是正确分工。

---

## 四、明确剔除、不宜作为开源交付的部分

| 类型 | 材料中的例子 | 处理 |
|------|--------------|------|
| 第三方版权正文 | `books/**` 原作与续写全文 | 不进开源仓库；仅本地私用 |
| 成人向内容库 | nsfw 分架书目 | 架构可支持分级，但示例数据需自产合规样例 |
| 定向镜像/站点抓取 | 针对特定站点的 ingest 脚本与 race 日志 | 不公开；最多提供「用户自有文件导入」通用接口 |
| 私有会话与密钥 | ST `data/default-user`、cookie-secret | 不备份进新项目 refs |
| 把聊天当真相源 | 依赖 ST 记忆续写 | 产品上明确反对；文件/DB 才是 SoT |

**开源友好替代：**

- 用虚构 demo 书（短、原创、CC0）演示流水线。  
- 导入：txt/epub/md + 用户粘贴；导出：md/docx/epub + 可选 ST 格式。  
- 抓取：不内置；文档说明「用户自行准备合法文本」。

---

## 五、合成一张「开源小说 Helper」能力骨架（供决策，非定稿）

若要对齐闭源写作助手的「能力面」，材料给出的骨架是：

```
┌─────────────────────────────────────────────────────────┐
│  项目（Book）沙箱                                        │
│  meta · sources · canon · continuity · outline · text    │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   解析 Agent          写作 Agent          审校 / 导出
   拆角色世界          续写/改写/扩写       OOC·一致性
   证据链              brief 驱动           格式导出
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
              上下文装配（优先级 + token 预算）
                            │
              BYOK / 本地模型（不锁厂商）
```

**材料已证明可行的差异化：**

1. **文件即工程** — 可被 Cursor/Claude Code 类 Agent 直接操作。  
2. **Canon/Continuity 双轨** — 比「一个 Story Bible 大杂烩」更适合长篇。  
3. **证据链解析** — 闭源产品少见、开源可做深。  
4. **ST 兼容导出** — 触达现有角色扮演/写作社区，而不被 ST 绑架。  
5. **本地优先 + 一书隔离** — 隐私与多项目安全。

**材料未覆盖、需产品层另补的（商业闭源常有）：**

- 场景级可视化大纲 / Beat board  
- 内嵌所见即所得编辑器体验  
- 一键「Story Engine」从梗概到成书向导  
- 协作 / 云同步 / 移动端  
- 付费模型托管（若坚持开源可只做 BYOK）

---

## 六、一句话总结

- **novel-lab**：把长篇小说当成**可版本化的工程仓库**，用 Agent 任务契约维护设定与正文一致性。  
- **silly-tavern**：把 LLM 交互做成**可扩展的提示装配前端**，擅长角色与世界书，不擅长书稿工程。  
- **新开源项目应取前者为骨、后者为筋**（可选兼容），并自觉剔除版权库与灰产抓取。
