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

<!-- Decision overrides (¶4) -->

- **Decision override:** 人设私有记忆作为真实能力（覆盖 spec §8 OQ1 默认「全共享、无私有记忆」）— rationale: 用户在设计评审（critic 阶段）要求保留，本迭代就做。

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
2. **共享桌面作为单一事实来源** — 每场会话一张 append-only 共享桌面（session 级 namespace `brainstorm:{session_id}:stream`），发言按序追加、标注发言者；人设基于共享桌面生成下一条发言（经窗口化注入，见 §8）。顺序是「0 丢失/重复」不变量的载体。
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

### 启动会话 — 配置校验（AC-01 · AC-02 · AC-03 · AC-13）

```mermaid
sequenceDiagram
    autonumber
    participant C as <client>
    participant S as <service>
    participant D as <data-store>

    Note over C,S: Precondition: 发起人已提供主题与人设名单（声明式配置）
    C->>S: 启动会话（提交主题 + 人设名单）
    S->>S: 校验配置：主题非空、人设去重后至少两位、每人设有角色描述
    alt 主题为空
        S-->>C: 拒绝启动（主题不能为空）
    else 人设去重后不足两位
        S-->>C: 拒绝启动（至少需要两位参与者）
    else 某人设缺少角色描述
        S-->>C: 拒绝加载（该人设必须提供角色描述）
    else 校验通过
        S->>D: 写入会话状态、主题、人设名单
        Note over S,D: persists Session（session_id、主题、人设名单、停止条件）
        D-->>S: 确认落盘
        S-->>C: 会话已开始
    end
    Note over C,S: Postcondition: 会话已创建并持久化，或启动被阻止且无任何会话写入
```

### 接力发言 — 生成失败重试与轮次名额（AC-04b · AC-15）

```mermaid
sequenceDiagram
    autonumber
    participant S as <service>
    participant X as <external-system>
    participant D as <data-store>

    Note over S,X: Precondition: 会话进行中，调度器选定某位参与者为本轮发言者
    S->>S: 检查该参与者本轮发言名额
    alt 本轮已发言（重复追加）
        S-->>S: 阻止追加（本轮发言名额已用）
    else 名额可用
        S->>X: 请求生成发言（注入主题 + 历史发言窗口）
        X-->>S: 发言文本，或生成失败
        alt 生成失败（超时或结果为空）
            Note over S,X: 重试 N 次（退避），仍失败则跳过
            S->>D: 记录跳过该参与者及失败原因
            Note over S,D: persists 跳过记录（发言者、轮次、失败原因）
            D-->>S: 确认落盘
            Note over S: 会话继续推进（调度器选下一位）
        else 生成成功
            S->>D: 追加发言到共享桌面（带顺序号 + 发言者）
            Note over S,D: persists Speech（追加顺序号、发言者、文本）
            D-->>S: 确认落盘
        end
    end
    Note over S,D: Postcondition: 本轮落桌一条发言，或跳过并记录；单轮内绝不二次追加
```

### 共享桌面 — 顺序读取与跨会话隔离（AC-05 · AC-06 · AC-06b）

```mermaid
sequenceDiagram
    autonumber
    participant S as <service>
    participant D as <data-store>

    Note over S,D: Precondition: 会话 A 进行中，参与者 a 属于会话 A，会话 B 是另一场会话
    S->>D: 按会话 A 的命名空间读取共享桌面
    D-->>S: 完整、按序、标注发言者的发言列表
    Note over S,D: 读范围限于会话 A 的命名空间，不越界
    Note over S,D: 隔离为构造保证：读/写 API 仅绑定本会话命名空间，参与者无法命名会话 B 的命名空间，故无运行时拒绝分支
    Note over S,D: Postcondition: 本会话内可见完整有序发言，会话 B 桌面保持不变、内容不暴露
```

### 路由者调度 — 选人、无效回退、收敛（AC-07 · AC-07b · AC-08）

```mermaid
sequenceDiagram
    autonumber
    participant S as <service>
    participant X as <external-system>
    participant D as <data-store>

    Note over S,X: Precondition: 会话启用了路由者，某位参与者刚完成发言
    S->>X: 调度路由者（结合桌面上下文与停止条件生成裁决）
    X-->>S: 路由者裁决（选定下一位，或宣布收敛）
    alt 宣布收敛
        S->>D: 记录收敛结论
        Note over S,D: persists 收敛状态 + 结论
        D-->>S: 确认落盘
        S->>S: 交停止条件处理，结束会话
    else 选定下一位发言者
        S->>S: 校验该发言者是否在人设名单内
        alt 不在名单内
            S->>S: 回退到固定轮转顺序选取下一位
            S->>D: 记录本次无效选择
            Note over S,D: persists 无效选择记录
            D-->>S: 确认落盘
        else 在名单内
            Note over S: 按路由者选定推进下一轮
        end
    end
    Note over S,X: Postcondition: 下一发言者合法（或回退固定轮转），收敛则交停止条件结束会话
```

### 自动停止 — 固定轮数 / 收敛 / 上限兜底（AC-09 · AC-10 · AC-10b）

```mermaid
sequenceDiagram
    autonumber
    participant S as <service>
    participant D as <data-store>

    Note over S,D: Precondition: 会话进行中，每轮落桌后执行停止判定
    S->>S: 判定停止条件
    alt 固定轮数（已达配置轮数）
        S->>D: 标记会话结束，产出完整讨论记录
        Note over S,D: persists 会话结束状态 + 完整记录
        D-->>S: 确认落盘
        S->>S: 返回完整讨论记录
    else 收敛判定（路由者已宣布收敛）
        S->>D: 标记会话结束，附带结论或摘要
        Note over S,D: persists 结论或摘要
        D-->>S: 确认落盘
        S->>S: 返回结论
    else 收敛判定但达最大轮数上限仍未收敛
        S->>D: 强制结束，标注未收敛
        Note over S,D: persists 结束状态 + 未收敛标记
        D-->>S: 确认落盘
        S->>S: 返回记录（标注未收敛）
    end
    Note over S,D: Postcondition: 会话按停止条件结束，产出完整记录（或结论、未收敛标注）
```

### 手动停止 — 在途发言不丢失（AC-11 · AC-11b）

```mermaid
sequenceDiagram
    autonumber
    participant C as <client>
    participant S as <service>
    participant X as <external-system>
    participant D as <data-store>

    Note over C,S: Precondition: 会话进行中，配置为手动停止
    C->>S: 发出停止指令
    S->>S: 检查是否有在途发言生成中
    alt 有在途发言生成中
        S->>X: 等待在途发言返回
        X-->>S: 发言文本
        S->>D: 追加在途发言到共享桌面
        Note over S,D: persists Speech（顺序号、发言者、文本）
        D-->>S: 确认落盘
    else 无在途发言
        Note over S: 立即进入结束
    end
    S->>D: 结束会话，保留当前讨论记录
    Note over S,D: persists 会话结束状态 + 当前记录
    D-->>S: 确认落盘
    S-->>C: 会话已结束，附讨论记录
    Note over C,S: Postcondition: 停止后会话结束，在途发言（若有）已落桌，无丢失
```

### 声明式配置与扩展点生效（AC-12 · AC-14）

```mermaid
sequenceDiagram
    autonumber
    participant C as <client>
    participant S as <service>
    participant D as <data-store>

    Note over C,S: Precondition: 发起人已声明式改动人设名单或停止条件，并定义了一个占位扩展（如回显名字的角色）
    C->>S: 启动会话（提交新配置 + 占位扩展）
    S->>S: 从声明式配置读取，并注册扩展（占位角色）
    S->>D: 写入会话状态（按新配置）
    Note over S,D: persists Session（新配置 + 注册的扩展）
    D-->>S: 确认落盘
    Note over S: 会话循环到达占位角色时，经扩展点调用
    S->>S: 占位角色经扩展点执行（回显名字），内核循环未改动
    S->>D: 追加占位角色发言到共享桌面
    Note over S,D: persists Speech（顺序号、发言者、文本）
    D-->>S: 确认落盘
    S-->>C: 会话运行中，新配置与占位扩展已生效
    Note over C,S: Postcondition: 新配置无需改代码即生效，扩展点接入的新角色运行且内核未改动
```

**Flagged items（sequences 阶段记录，不改动既有块）:**

- **参与者词汇不一致**：既有 F1 用具体参与者 `Host / CLI / Engine / Weave / LLM / Store`，本阶段新增流程统一用泛化词汇 `<client> / <service> / <data-store> / <external-system>`。按「不重写既有块」规则 F1 保留原样，交由 `design` 决定是否回改 F1 对齐泛化词汇。
- **event_bus 未画作参与者**：ADR-0004 规定事件总线仅作观测、不承载控制流，故全部流程为同步编排，未引入 `<message-bus>` 参与者，也无幂等键/死信分支。
- **失败语义的具体参数仍开放**：F3（AC-04b）与 F7（AC-11b）画出了失败形状（重试 N 次后跳过、等待在途发言落桌），但重试次数 N、退避策略等具体参数仍未定，由 `data-model` / `tasks` / `implement` 落实（呼应 §11 已接受的债务）。

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

| Concept | Convention | Where defined |
|---|---|---|
| Logging | 结构化日志，字段 `module=<name>`、`session_id` | 此处（§8） |
| Error handling | 领域哨兵错误 → 适配层错误映射 → CLI 退出码/提示 | 此处（§8） |
| Authorization / Isolation | 会话按 namespace 隔离（`brainstorm:{session_id}:*` 共享 + `persona:{id}:*` 私有）；跨会话/跨人设读写被拒绝 | ADR-0003 / ADR-0006；spec §6.1 |
| ID strategy | `session_id`（会话）、发言按追加顺序号 | 此处（§8） |
| Internationalisation | N/A，单语言（zh） | — |
| Observability | event_bus 进度事件 + 会话/回合边界 span | ADR-0004；§7 |
| Events | 进度事件（回合开始/发言落桌/收敛/停止），不承载控制流 | ADR-0004 |
| Context-window injection | 共享桌面注入人设上下文：截断到最近 N 条 + 可选摘要（v1 固定 N=20；可配置化随引擎泛化 roadmap 步骤 2 吸收） | 此处（§8，spec §8 OQ 默认） |

## 9. Architecture decisions

| # | Title | Status | Section |
|---|---|---|---|
| 0001 | Build the brainstorm engine as a library-sdk driven by a CLI | Accepted | §4 |
| 0002 | Keep the engine kernel minimal (orchestration loop only) | Accepted | §4 |
| 0003 | Persist sessions in a single SQLite store with resume-at-round | Accepted | §4 |
| 0004 | Orchestrate turns synchronously; use the event bus for observability only | Accepted | §4 |
| 0005 | Give each session its own Weave instance | Accepted | §4 |
| 0006 | Give each persona private memory alongside the shared table | Accepted | §4 |

ADR files live under `docs/features/brainstorm/adr/NNNN-<title>.md`.

## 10. Quality requirements

Each top-3 goal from §1 expanded into a full scenario:

**QG-1. 一致性/耐久**
- **When:** 会话进行中，多个人设多次追加发言。
- **Then:** 桌面完整、有序地包含每一次发言并标注发言者；每场会话 0 条丢失或重复发言。
- **How verify:** 追加顺序不变量测试（spec §6 一致性/耐久行）。

**QG-2. 会话可靠性**
- **When:** 会话进行中遇到进程崩溃 / LLM 失败 / 超时 / 断连。
- **Then:** 已开始的会话 99.9% 不被意外中断；恢复到中断那一轮、已落桌发言不重放。
- **How verify:** 耐久测试（进程崩溃 / LLM 失败 / 超时 / 断连场景，spec §6）。

**QG-3. 可扩展性**
- **When:** 新增一个角色 / 调度策略 / 停止条件 / 消费界面。
- **Then:** 0 处内核改动（经扩展点接入，ADR-0002）。
- **How verify:** 内核边界由 design 定义后，审查变更范围是否触及内核（spec §6 可扩展性行）。

## 11. Risks and technical debt

| Risk / debt | Severity | Mitigation | Owner |
|---|---|---|---|
| Effort budget / deadline 未定（spec 未引） | Medium | 补齐 PM 预算与截止日期，否则范围易漂移 | PM |
| 失败处理（重试/跳过/在途停止）未在本设计会话展开 | Medium | `sequences` 阶段按 AC-04b / AC-11b 覆盖；本 SAD 不承诺失败语义 | Tech Lead |
| demo「每 persona 隔离」在 stream 层已失效（`world:shared:stream` 累积所有发言） | Medium | 新引擎用 `brainstorm:{session_id}:*` 专用 namespace，不复用 demo 的 world scope | Tech Lead |
| SQLite 单文件 WAL 单写者，极端并发写有上限 | Low | ≥5 会话舒适；数十量级再评估进程池/多进程（§7） | Backend |
| 上下文注入截断 N 为固定配置，无自适应 | Low | v1 接受；未来可加自适应/摘要 | Backend |

**Accepted debt (acceptable in v1, plan to fix later):**
- 失败语义（重试次数、跳过策略、在途发言停止）未定——本设计不覆盖，交 `sequences` / `implement` 后续。
- 进度事件无 schema 版本化（仅观测，未来消费方多时再版本化）。

> Product 自有开放问题（默认人设名单、未来分支优先级）跟踪于 spec §8，不在此重复。

## 12. Glossary

| Term | Meaning |
|---|---|
| 发起人（Host） | 提供主题、选定人设与配置、启动/停止会话的人或系统；本身不发言 |
| 参与者（Persona / 人设） | 具名、带角色描述的 AI 角色，按序在共享桌面发言 |
| 路由者（Moderator） | 可选的参与者型角色，在每次发言后决定下一位发言者并判断收敛 |
| 主题（Topic） | 头脑风暴要讨论的问题或命题 |
| 共享桌面（Shared Table） | 会话内所有发言按序累积、对所有参与者可见的讨论记录（append-only） |
| 发言（Speech / Utterance） | 某参与者对主题与历史发言的一次贡献，落到桌面并标注发言者 |
| 会话（Session） | 一次头脑风暴实例，含主题、人设名单、共享桌面与停止条件 |
| 轮（Round） | 固定轮转模式下所有人设各发言一次；但「固定轮数」停止条件按发言条数计（N 条 = 结束，spec §8 OQ 默认） |
| 停止条件（Stop Condition） | 会话结束的判据（固定轮数 / 收敛判定 / 手动停止） |
| 收敛（Convergence） | 讨论被判定为「已达成结论」的状态 |
| 表面（Surface） | 特性拥有的 C4 容器；本特性为 library-sdk（引擎）+ cli（驱动器） |
| 内核（Kernel） | 会话编排循环 + 共享桌面 + 扩展注册表；最小且稳定（ADR-0002） |
| 扩展点（Extension point） | 可插拔的能力接口：角色 / 调度策略 / 停止条件 / 消费界面（ADR-0002） |
| 调度策略（Scheduling strategy） | 决定下一位发言者的策略（固定轮转 / 路由者） |
| 命名空间（Namespace） | `brainstorm:{session_id}:stream|state`（会话共享，ADR-0003）+ `persona:{id}:stream|state`（人设私有，ADR-0006） |
| 人设私有记忆（Private Memory） | 每人设私有、他人不可见的记忆/便签（ADR-0006） |
