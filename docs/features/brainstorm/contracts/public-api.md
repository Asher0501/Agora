---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
---

# Public API — brainstorm（library-sdk）

> **契约来源（单向派生，非手写）：** 本文件是 `data-model.md`（类型与约束）+ `sad.md` §6 序列（错误分支 + 观测事件）+ `spec.md` §4/§5（能力清单与验收）的派生结果。表面为 `library-sdk`（引擎公开 Python API 即契约，ADR-0001）；`cli` 表面另有 `contracts/cli.md`。逐字段溯源见 `contracts/api-sync-report.md`（Section A）。本文件 `# inferred` 标注的项为低置信度推断，见该报告 Section B。

## 1. Scope & consumers

引擎核心以**库**形态交付（ADR-0001）：公开 Python API（会话生命周期 + 扩展注册 + 读取讨论记录）即契约。业务层（`business/`）零 weave 依赖（sad §2 约定）。今天的唯一消费方是 CLI（`contracts/cli.md`）；未来 Web 前端 / 观察者角色经**扩展点**接入（ADR-0002），不改内核。

**内核不可插拔部分**（ADR-0002）：会话生命周期、回合编排循环、共享桌面（append-only、标记发言者）、扩展注册表。**四个扩展点**：角色、调度策略、停止条件、消费界面——见 §4。

## 2. Domain types

类型均来自 `data-model.md` 实体，字段约束照抄。

### SessionConfig（= data-model `SESSION.config`）

| Field | Type | Constraint | Origin |
|---|---|---|---|
| `topic` | `str` | 非空（AC-02） | `SESSION.config.topic` |
| `personas` | `list[PersonaConfig]` | 去重后 ≥2（AC-03） | `SESSION.config.personas` |
| `scheduler` | `SchedulerKind` | 枚举 | `SESSION.config.scheduler` |
| `stop_condition` | `StopConditionConfig` | — | `SESSION.config.stop_condition` |

### PersonaConfig（= `SESSION.config.personas[]`，即 `PERSONA_INSTANCE`）

| Field | Type | Constraint | Origin |
|---|---|---|---|
| `persona_id` | `str` | 非空 | `PERSONA_INSTANCE.persona_id` |
| `name` | `str` | — | `SESSION.config.personas[].name` |
| `role_description` | `str` | 必填（AC-13） | `PERSONA_INSTANCE.role_description` |

### SchedulerKind = `"round_robin" | "moderator"`（= `SESSION.config.scheduler`；ADR-0002 扩展点）

### StopConditionConfig（= `SESSION.config.stop_condition`）

| Field | Type | Constraint | Origin |
|---|---|---|---|
| `type` | `StopConditionKind` | 枚举 | `SESSION.config.stop_condition.type` |
| `max_speeches` | `int | None` | `>0` 时生效；收敛判定的兜底上限（AC-10b） | `SESSION.config.stop_condition.max_speeches` |

### StopConditionKind = `"fixed_rounds" | "convergence" | "manual"`（= `SESSION.config.stop_condition.type`）

### Session（= `SESSION` 聚合根）

| Field | Type | Origin |
|---|---|---|
| `session_id` | `str` (UUID) | `SESSION.session_id` |
| `topic` | `str` | `SESSION.topic` |
| `personas` | `list[PersonaConfig]` | `SESSION.personas` |
| `scheduler` | `SchedulerKind` | `SESSION.scheduler` |
| `stop_condition` | `StopConditionConfig` | `SESSION.stop_condition` |
| `status` | `SessionStatus` | `SESSION.status` |
| `current_seq` | `int` | `SESSION.current_seq` |
| `created_at` | `float` | `SESSION.created_at` |

### SessionStatus = `"running" | "stopped"`（= `SESSION.status`）

### Speech（= `SPEECH` 实体，共享桌面一条）

| Field | Type | Origin |
|---|---|---|
| `seq` | `int` | `SPEECH.seq`（会话内严格单调） |
| `speaker_id` | `str` | `SPEECH.speaker_id` |
| `text` | `str` | `SPEECH.text` |
| `created_at` | `float` | `SPEECH.created_at` |

### SessionOutcome（会话结束产出 = `SESSION.conclusion` + 完整记录）

| Field | Type | Origin |
|---|---|---|
| `session_id` | `str` | `SESSION.session_id` |
| `status` | `SessionStatus`（=`"stopped"`） | `SESSION.status` |
| `converged` | `bool` | `SESSION.conclusion.converged` |
| `conclusion` | `str | None` | `SESSION.conclusion.conclusion`（AC-10；AC-10b 时为 `None`） |
| `speeches` | `list[Speech]` | 共享桌面全量（`SPEECH` 按 `seq` 升序） |

## 3. Engine operations（生命周期 + 读取 + 注册）

每项标出 AC 溯源与可抛出的错误（见 §5）。

### `create_session(config: SessionConfig) -> Session`

- **US-01 / AC-01·02·03·13 / sad §6「启动会话」**
- 校验顺序：`topic` 非空 → 否则 `session.topic_required`；`personas` 去重后 ≥2 → 否则 `session.insufficient_personas`；任一 persona 缺 `role_description` → `session.persona_role_required`。校验全通过才写 `SESSION.config`（启动时写一次；AC-12 新配置即新会话）。

### `run_session(session_id: str) -> SessionOutcome`

- **US-02·03·04·05 / AC-04·04b·07·07b·08·09·10·10b·15 / sad §6 F1·F3·F5·F6**
- 驱动回合循环至停止条件成立：调度器选下一发言者 → 角色生成（注入主题 + 历史窗口）→ 追加共享桌面（带 `seq`）→ 判停止。
- 单轮内同一发言者二次追加 → `session.round_quota_exhausted`（AC-15）。
- 生成失败重试 N 次仍失败 → 跳过并记录（**系统事件**，非错误；AC-04b）。
- 路由者选定下一位不在名单内 → 回退固定轮转并记录（**系统事件**；AC-07b）。

### `stop_session(session_id: str) -> SessionOutcome`

- **US-05 / AC-11·11b / sad §6「手动停止」**
- 有在途发言生成时先等待其落桌再结束（AC-11b），保证该发言不丢失。

### `resume_session(session_id: str) -> Session`

- **ADR-0003 / spec §8 OQ3**：恢复到中断那一轮，已落桌发言不重放。

### `read_table(session_id: str) -> list[Speech]`

- **US-03 / AC-05 / sad §6「共享桌面」**：按 `session_id` 的 namespace 读取，返回完整、有序（`seq` 升序）、标注 `speaker_id` 的发言列表。越界读取被 namespace 隔离拒绝（AC-06b）。

### 扩展注册（US-07 / AC-14 / sad §6「声明式配置与扩展点生效」）

```
register_role(role: Role) -> None
register_scheduler(scheduler: Scheduler) -> None
register_stop_condition(cond: StopCondition) -> None
register_consumer(consumer: Consumer) -> None
```

装配时注册默认实现（`round_robin` 调度、`fixed_rounds` 停止、CLI 消费）；自定义实现经同一注册点接入，内核循环不改动（AC-14）。

## 4. Extension points（协议）

四个可插拔接口（ADR-0002）。实现者自定义；签名即契约。

### Role（角色）

```python
class Role(Protocol):
    async def speak(self, ctx: RoleContext) -> str
```

- `RoleContext`：`topic: str`、`history: list[Speech]`（窗口化截断，sad §8）、`private_memory: PrivateMemory`（本角色私有记忆句柄，ADR-0006 `# inferred`）。
- 发言者由系统标注（`speaker_id` 来自人设 id），不以内容自称为准（spec §6.1 冒名发言防线）。

### Scheduler（调度策略）

```python
class Scheduler(Protocol):
    def next_speaker(self, ctx: SchedulerContext) -> str  # 返回 persona_id
```

- 默认实现 `round_robin`；`moderator` 调度时由路由者角色在每次发言后裁决（AC-07）。

### StopCondition（停止条件）

```python
class StopCondition(Protocol):
    def evaluate(self, ctx: StopConditionContext) -> StopDecision
```

- `StopDecision = Stop | Continue`；`fixed_rounds`（按发言条数计，spec §8 OQ 默认）、`convergence`（路由者宣告）、`manual`（发起人指令）三种默认实现（AC-09·10·10b·11）。

### Consumer（消费界面）

```python
class Consumer(Protocol):
    def on_event(self, event: ProgressEvent) -> None
```

- 订阅观测进度事件（§6）；CLI 是今天的默认实现。事件只读、不承载控制流（ADR-0004）。

## 5. Error sentinels

统一信封 `{code, message, details?}`；`code` 用中性 `module.error_name` 蛇形命名，模块前缀 `session`。**本仓库尚无错误注册表**（`14_forum` 为全新工程）——以下 `code` 为契约提案，待 `implement` 落地（见 api-sync-report 第 2 点）。

| code | 触发（AC / 序列） | 状态类 |
|---|---|---|
| `session.topic_required` | AC-02 主题为空 | 配置（4xx） |
| `session.insufficient_personas` | AC-03 去重后不足两位 | 配置（4xx） |
| `session.persona_role_required` | AC-13 缺角色描述 | 配置（4xx） |
| `session.round_quota_exhausted` | AC-15 单轮二次追加 | 领域状态（4xx） |
| `session.not_found` | `# inferred` 操作不存在的 session_id | 未覆盖（序列缺口） |
| `session.invalid_state` | `# inferred` 对已停止会话 run/stop | 未覆盖（序列缺口） |

> 后两行为 `# inferred`（低置信度）——spec §5 与 sad §6 均未覆盖「对不存在的 / 已结束的会话操作」，作为**序列缺口**在 api-sync-report 记 Open Question（owner: sequences）。
>
> 跨会话隔离（AC-06/06b）由 namespace **构造保证**：读/写 API 仅绑定本会话命名空间、无跨会话入口，故没有对应的运行时拒绝错误码（已删除 `session.cross_session_write/read`）。

## 6. Observability events（ADR-0004，仅供观测）

进程内 `event_bus` 发布，`Consumer` 订阅；不承载控制流。事件名用中性 `module.action` 命名：

| event | 载荷 | 触发点 |
|---|---|---|
| `session.turn_started` | `{session_id, seq, speaker_id}` | 每轮开始 |
| `session.speech_landed` | `{session_id, seq, speaker_id}` | 发言追加桌面后 |
| `session.converged` | `{session_id, conclusion}` | 路由者宣告收敛 |
| `session.stopped` | `{session_id, status}` | 会话结束 |

> 进度事件无 schema 版本化（sad §11 已接受债务：仅观测，未来消费方多时再版本化）。
