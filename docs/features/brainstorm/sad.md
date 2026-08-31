---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-08-31"
feature_size: "M"
target_surfaces: [library-sdk, cli]  # filled in §4 — subset of: backend-service | web-frontend | mobile-app | desktop-app | cli | worker | library-sdk. Read (never re-derived) by api/sequences/tasks/plan-tests/review → _shared/surfaces.md
---

# Software Architecture Document — brainstorm

<!-- 12 Arc42 sections. Empty section → <!-- N/A: <one-line reason> -->. -->
<!-- C4 Context (L1) lives inline in §3. C4 Container (L2) lives inline in §5. -->
<!-- Numbers in §10 come VERBATIM from spec.md §6 NFR — no inventing, no rounding. -->

## 1. Introduction and goals

**Intent.** 把 weave demo「多个人设各自独立回答同一问题、记忆彼此隔离」的演示，升级成「多个人设围绕一个主题、按序接力发言、所有发言共享可见」的头脑风暴机制。目标用户是**发起人（Host）**：在开题、产品决策、技术方案之前，让一组不同视角的 AI 角色围绕一个主题对撞想法，随后阅读讨论记录提炼结论。引擎设计为「稳定内核 + 可插拔扩展点」，先在后端把能力做全、由命令行驱动；角色、调度策略、停止条件、消费界面都是扩展点。

**Top-3 quality goals（一行一句；完整场景在 §10）**

1. **一致性/耐久** — 每场会话 0 条丢失或重复发言（追加顺序不变量）。
2. **会话可靠性** — 已开始的会话 99.9% 不被意外中断，可恢复到中断那一轮。
3. **可扩展性** — 新增一个角色/策略/界面 = 0 处内核改动。

**Stakeholders（角色取自 CONTEXT 术语表，不杜撰）**

| Role | Interest | Sign-off owner? |
|---|---|---|
| 发起人（Host） | 发起、配置、停止会话；阅读讨论记录 | No |
| 参与者（Persona） | 按序在共享桌面发言 | No |
| 路由者（Moderator） | 决定发言顺序与收敛（可选） | No |
| Tech Lead | SAD 审批 | Yes |
| Security Lead | 安全审查（§6.1 多角色生成边界 + 提示词注入面） | No |

<!-- Decision overrides (¶4) — populated by the critic resolution loop, empty otherwise. -->

## 2. Constraints

**Technical.**
- Python 3.11+（weave `requires-python = ">=3.11"`）。
- weave **0.1.0**（外部依赖，来自 `13_weave`，`pip install -e .`；核心仅依赖 PyYAML）。
- SQLite（沿用 demo `memory.db` 单库、`memory_entries` 表、namespace 隔离）。
- LLM 经 weave 的 `BaseLLM` 适配接入（deepseek / anthropic / openai 可插拔；离线用 `FakeLLM`）。
- **代码归属**：本特性在 `14_forum` 新工程实现，weave 为外部依赖（不改 weave 源码）。
- 架构约定：分层沿用 demo —— `business/` 零 weave 依赖、`weave_adapter/` 唯一接入点、配置全部来自 YAML、零硬编码。

**Organisational.**
- Effort budget — `<TBD by PM>`（spec 未引，§11 记一条待定）。
- Deadline — `<TBD by PM>`。
- Team — 单人（Asher）。

**Conventions.**
- 依赖方向单向（demo `README.md:38-58`）：`business/` 不 import weave；`weave_adapter/` 是唯一集成点；作用域名 / world_id / 提示词变量 / 状态键全部读自 YAML，零字面量。
- 命名：`session`（会话）、`speech/utterance`（发言）、`round`（轮）、`shared_table`（共享桌面）。
- 命名空间/隔离：`brainstorm:{session_id}:stream|state` —— 会话级隔离（沿用 weave namespace 机制）。

**Regulatory / external.**
- Data classification: **internal**（spec §6.1 —— 记录含未定稿产品/技术推理）。
- Personal data: **无**（人设均为虚构角色）。
- Security review: **Required**（多角色生成边界 + 提示词注入面）。

## 3. Context and scope

brainstorm 引擎让**发起人（Host）**用一份声明式配置（主题 + 人设名单 + 停止条件）开启一场会话，多个 AI **人设（Persona）**围绕主题按序接力发言，每次发言落到一张所有参与者可见的**共享桌面**，可选的**路由者（Moderator）**决定发言顺序与收敛。系统本地运行、由命令行驱动，未来经扩展点接前端（论坛界面等）。

<!-- brownfield: 复用 13_weave 框架 + demo（weave_adapter 唯一集成点；SQLite namespace 隔离） -->

**External systems (in / out):**

| Actor or system | Type | Interaction |
|---|---|---|
| 发起人（Host） | Person | 配置主题/人设/停止条件，启动/停止会话，阅读讨论记录 |
| weave 框架 0.1.0 | System (external) | 提供 Loop / Memory / LLM 适配能力；唯一接入点 |
| LLM 提供方 | System (external) | 生成人设发言文本（deepseek / anthropic / openai） |
| SQLite 记忆库 | System (external datastore) | 持久化共享桌面、会话状态、人设私有记忆 |

**信任边界**：主题与人设配置按不可信数据对待（spec §6.1 提示词注入面）；LLM 输出按不可信数据对待；跨会话读写被 namespace 隔离拒绝。

**C4 Context (L1):**

```mermaid
C4Context
    title brainstorm — System Context

    Person(host, "发起人 Host", "配置主题/人设/停止条件，启动/停止会话，阅读讨论记录")
    System(app, "Brainstorm 引擎", "围绕主题按序接力发言的会话编排引擎")
    System_Ext(weave, "weave 框架 0.1.0", "Loop / Memory / LLM 适配能力")
    System_Ext(llm, "LLM 提供方", "生成人设发言文本")
    SystemDb(store, "SQLite 记忆库", "共享桌面、会话状态、人设私有记忆")

    Rel(host, app, "配置/启动/停止会话", "CLI")
    Rel(app, weave, "驱动人设回合", "import")
    Rel(app, llm, "生成发言", "SDK/HTTP")
    Rel(app, store, "读写桌面与状态", "sqlite3")
```

## 4. Solution strategy

**目标表面（Target surfaces）**：`library-sdk`（引擎核心，公开 Python API 即契约）+ `cli`（命令行驱动器）——见 frontmatter `target_surfaces` 与 ADR-0001。本迭代无 UI 表面（spec §3 非目标「不实现 Web 前端」）。

**Top strategic choices（ADR 的种子）**

1. **最小内核 + 可插拔扩展点**（ADR-0002）— 内核只含四样：会话生命周期、回合编排循环、共享桌面（append-only、标记发言者）、扩展注册表；角色、调度策略、停止条件、消费界面是四个扩展点，装配时注册默认实现。这是 spec §1「稳定内核 + 可插拔扩展点」的落地。
2. **共享桌面作为单一事实来源** — 每场会话一张 append-only 共享桌面（session 级 namespace `brainstorm:{session_id}:stream`），发言按序追加、标注发言者；人设读完整桌面后生成下一条发言。顺序是「0 丢失/重复」不变量的载体。
3. **同步进程内编排 + 事件仅用于观测**（ADR-0004）— 回合推进（选下一发言者 → 调角色生成 → 追加桌面 → 判停止）走同步调用；weave `event_bus` 只发进度事件，不承载控制流。
4. **单库持久化 + 会话级隔离 + 可恢复**（ADR-0003）— 单一 SQLite 库，会话按 namespace 隔离；发言落盘即追加；崩溃恢复到中断那一轮、已落桌不重放。
5. **每会话独立 weave 实例**（ADR-0005）— 每个会话一个独立 `Weave` 实例（各自 loop/LLM/记忆状态），会话作为独立 async 任务并发；共享 SQLite 文件用 WAL 模式承载并发写。

每个战术决策应追溯到这些种子之一；与种子矛盾的战术决策是红旗，在 §11 揭示。

## 5. Building block view

**分层风格**：六边形/clean —— 沿用 demo 的依赖方向：`business/` 纯领域类型（零 weave 依赖）、`weave_adapter/` 是唯一 weave 集成点、配置全部来自 YAML；内核 `engine/` 只做编排，扩展点 `extensions/` 承载可插拔实现（ADR-0002）。

**Internal decomposition:**

```
brainstorm/                      # 新工程（14_forum）
├── engine/                      # 内核：会话循环 + 共享桌面 + 扩展注册表
├── extensions/                  # 默认扩展实现（可插拔）
│   ├── roles/                   # 人设角色、路由者
│   ├── schedulers/              # 固定轮转、路由者调度
│   ├── stop_conditions/         # 固定轮数、收敛、手动
│   └── consumers/               # CLI 消费、进度观测
├── business/                    # 纯领域类型（零 weave）：Session / Speech / SharedTable / Config
├── weave_adapter/               # 唯一 weave 集成点：PersonaAgent + 作用域配置
└── cli/                         # 命令行入口：commands / flags / exit-codes
```

**C4 Container (L2):**

```mermaid
C4Container
    title brainstorm — Containers

    Person(host, "发起人 Host")

    Container_Boundary(app, "brainstorm 工程") {
        Container(cli, "Brainstorm CLI", "Python", "命令行驱动：创建/运行/停止会话、导出记录")
        Container(engine, "Brainstorm 引擎 (library-sdk)", "Python", "会话编排内核 + 可插拔扩展点")
    }

    ContainerDb(store, "SQLite 记忆库", "SQLite", "共享桌面、会话状态、人设私有记忆")
    System_Ext(weave, "weave 框架 0.1.0", "Loop / Memory / LLM 适配")
    System_Ext(llm, "LLM 提供方", "生成发言文本")

    Rel(host, cli, "配置/启动/停止会话", "CLI")
    Rel(cli, engine, "调用引擎 API", "import")
    Rel(engine, weave, "驱动人设回合", "import")
    Rel(weave, llm, "生成发言", "SDK/HTTP")
    Rel(engine, store, "读写桌面与状态", "sqlite3")
```

## 6. Runtime view

**Critical flow 1: 固定轮转接力发言（happy path）**

```mermaid
sequenceDiagram
    participant Host
    participant CLI
    participant Engine
    participant Weave
    participant LLM
    participant Store

    Host->>CLI: 配置主题/人设/停止条件
    CLI->>Engine: 创建会话 (start)
    Engine->>Store: 写入会话状态 + 主题
    loop 每轮（固定轮转，直到停止条件）
        Engine->>Engine: 调度器选下一发言者
        Engine->>Weave: 驱动该人设生成发言 (arun)
        Weave->>LLM: 生成发言文本
        LLM-->>Weave: 发言文本
        Weave-->>Engine: 发言结果
        Engine->>Store: 追加发言到共享桌面（带顺序号）
        Engine->>Engine: 判停止条件
    end
    Engine-->>CLI: 会话结束 + 完整记录
    CLI-->>Host: 讨论记录
```

**错误/失败流（AC-04b 发言失败、AC-11b 在途发言停止等）**：本设计阶段不展开——失败处理另属独立问题域；交由 `sequences` 阶段按 §5 AC 逐条覆盖。

## 7. Deployment view

本地单进程部署：`brainstorm` CLI 在发起人机器运行，进程内启动引擎；每个会话一个独立 async 任务（ADR-0005），共享一个 SQLite 文件（WAL 模式）。无网络拓扑、无副本——本地命令行工具，非服务。

**Monitoring:**
- Metrics: `turn_overhead_p95_ms`（每轮编排开销 p95，spec §6 ≤100 ms）、`table_read_p95_ms`（读桌面 p95，spec §6 ≤50 ms）、`session_token_usage`（每会话 token，spec §7 KPI）。
- Alerts: 会话停滞（单轮无进展超阈值）→ 记录并提示发起人。
- Tracing: 在会话/回合边界打 span（发言落桌、停止判定）。

**Scaling thresholds:**
- 单进程舒适承载 ≥5 并发会话（内存随会话数线性，ADR-0005）。
- 会话数达数十量级时评估进程池/多进程；SQLite 单文件 WAL 为单写者，极端并发写另议（§11）。

## 8. Crosscutting concepts

<!-- 🎯 Why: CROSS-CUTTING PATTERNS spanning several modules: logging, errors, authorization, ID
     strategy, events, caching. ⭐ The second-densest section. A pattern inside one module is NOT
     here; a project-wide convention belongs in the convention file.
     📋 Write: a table — concept / convention / where defined. One row per concept.
     📌 e.g. «sortable time-based IDs generated in the app layer» as a default from the convention file. -->

| Concept | Convention | Where defined |
|---|---|---|
| Logging | <e.g. structured, fields `module=<name>`> | <convention file §X or here> |
| Authentication | <e.g. token-based via middleware> | <convention file §X> |
| Error handling | <e.g. domain sentinel → ports error mapping → JSON> | <convention file §X> |
| ID strategy | <e.g. sortable time-based ID in the app layer> | <convention file §X> |
| Internationalisation | <e.g. N/A, single language> | — |
| Observability | <e.g. tracing on the request boundary> | — |
| Events | <module-specific patterns, if any> | <here> |

## 9. Architecture decisions

<!-- 🎯 Why: the REVERSE INDEX onto the adr/ folder. `ls adr/` gives the files; §9 gives the
     semantics — why they exist, which SAD section they attach to, what status.
     📋 Write: a 4-column table, one row per ADR. Mixed status is fine.
     📌 e.g. «0001 | Store content as a table of typed blocks | Accepted | §4». -->

| # | Title | Status | Section |
|---|---|---|---|
| <NNNN> | <imperative — e.g. "Use a sliding-window counter for rate limiting"> | Accepted | §<N> |
| <NNNN> | <imperative — e.g. "Co-locate the worker in the API process"> | Accepted | §<N> |

ADR files live under `docs/features/<slug>/adr/NNNN-<title>.md`.

## 10. Quality requirements

<!-- 🎯 Why: the QUALITY TREE — take a goal from §1 and break it into concrete leaves: tests,
     metrics, configs, drills. ⭐ Without §10, §1 is a manifesto. With §10 each declaration maps
     to something PROVABLE.
     📋 Write: per §1 goal — When / Then / How-verify. Numbers from spec §6 NFR VERBATIM (don't
     round ≤250ms to ≤300ms — that's a critic F6 hit).
     📌 e.g. «p95 ≤ 500 ms on a block update, verified by a 100 req/s load test». -->

Each top-3 goal from §1 expanded into a full scenario:

**QG-1. <quality attribute>**
- **When:** <trigger condition>
- **Then:** <expected behaviour with numbers from spec §6 NFR>
- **How verify:** <test / chaos drill / load test / metric>

**QG-2. <quality attribute>**
- **When:** <trigger>
- **Then:** <expected>
- **How verify:** <how>

**QG-3. <quality attribute>**
- **When:** <trigger>
- **Then:** <expected>
- **How verify:** <how>

## 11. Risks and technical debt

<!-- 🎯 Why: ⭐ collects EVERYTHING that can break — not only the technical. Without §11 risks get
     discussed at standups and lost; debt lives only in the head of whoever accepted it.
     📋 Write: a risk/debt table — severity — mitigation — owner. Accepted debt in its own block.
     📌 The first risk is often a product risk, not a technical one. That's normal. -->

<!-- Severity literals: Low / Medium / High for regular risks; "Open question" for rows created by
     a Save-as-OQ resolution during the Socratic walk (see references/socratic.md). -->

| Risk / debt | Severity | Mitigation | Owner |
|---|---|---|---|
| <e.g. Worker lag may reach hours during a downstream outage> | Medium | <alert >10 min, on-call playbook, retry backoff> | <DevOps> |
| <e.g. No event-schema versioning in v1> | Medium | <ADR-NNNN planned for v2, tolerate unknown fields> | <Backend> |
| Open architectural decision: <decision-headline> | Open question | Resolve before <stage trigger or YYYY-MM-DD>; <inline rationale from the Save-as-OQ> | <owner> |

**Accepted debt (acceptable in v1, plan to fix later):**
- <e.g. the entity is immutable / unversioned — OK for v1, may need audit versioning in v2>

## 12. Glossary

<!-- 🎯 Why: ⭐ the DOMAIN GLOSSARY that ends arguments a year later («checkpoint — weekly or
     biweekly? quarter — calendar or fiscal?»).
     📋 Write: a term / meaning table. Business + technical terms mixed.
     📌 e.g. «Lesson | a unit inside a course made of blocks (text, video)». -->

| Term | Meaning |
|---|---|
| <e.g. domain object A> | <its meaning in this domain> |
| <e.g. domain object B> | <its meaning> |
| <e.g. domain invariant name> | <the rule, in plain language> |
