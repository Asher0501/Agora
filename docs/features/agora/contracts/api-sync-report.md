---
status: Draft
owner: "Asher"
updated_at: "2026-09-06"
feature_size: "L"
---

# API sync report — agora

> 双向漂移检查（`api` 阶段的结构性 self-check）。契约（`public-api.md` + `cli.md`）是 `data-model.md`（类型）+ `sad.md` §6（序列分支）+ `spec.md` §4/§5（能力）的派生产物——本报告核对派生是否忠实、并反哺上游缺口。界面种类：`library-sdk` + `cli`（`sad.md` frontmatter `target_surfaces`，ADR-0001）；无 backend-service / UI / worker 表面。

## A. Field-origins table

一列一个 `(symbol, field)`，确保契约里每个字段可溯源。`confidence`：high = 映射到 data-model 列/字段且类型约束一致；medium = 派生自 spec 字段名但无列；low = 仅序列消息名推断，待确认。

### A.1 类型（`agora.types`）

| schema_path | origin | confidence |
|---|---|---|
| RoleConfig.id | data-model §AGENT agent_id / config.scenario.roles[].id | high |
| RoleConfig.prompt | data-model §AGENT role_description（config.scenario.roles[].prompt） | high |
| RoleConfig.inject | atomic-relay §2 `inject`（data-model config.scenario.roles[].inject） | high |
| RoleConfig.window | data-model config.scenario.roles[].window | high |
| RoleConfig.output | data-model config.scenario.roles[].output（free_text\|pick_next\|verdict） | high |
| SelectConfig.type | data-model config.scenario.select.type（round_robin\|llm_pick） | high |
| SelectConfig.role | data-model config.scenario.select.role | high |
| StopConfig.type | data-model config.scenario.stop.type（fixed_rounds\|llm_verdict\|manual） | high |
| StopConfig.max | data-model config.scenario.stop.max | high |
| StopConfig.judge | data-model config.scenario.stop.judge | high |
| **SummaryConfig** | data-model config.scenario.summary（`role`/`key`/`window`，已 ratify） | high |
| ScenarioConfig.scenario | data-model config.scenario.name | high |
| RuntimeValues.topic | data-model config.runtime.topic | high |
| RuntimeValues.stance | data-model config.runtime.stance | high |
| Run.run_id | data-model §RUN run_id（uuid4） | high |
| Run.scenario | data-model §RUN scenario（config 快照，ADR-0006） | high |
| Run.status | data-model §RUN status.status（running\|stopped） | high |
| Run.current_seq | data-model §RUN current_seq（status.current_seq） | high |
| Run.verdict | data-model §RUN verdict | high |
| Run.recap | data-model §RUN recap | high |
| Turn.seq | data-model §TURN seq | high |
| Turn.agent_id | data-model §TURN agent_id | high |
| Turn.text | data-model §TURN text | high |
| Verdict.converged | data-model §RUN verdict.converged | high |
| Verdict.conclusion | data-model §RUN verdict.conclusion | high |
| Recap.termination | data-model §RUN recap.termination（converged\|fixed_rounds\|cap_unconverged\|manual） | high |
| Recap.recap | data-model §RUN recap.recap | high |

### A.2 命名空间（`agora.namespaces`）

| symbol | origin | confidence |
|---|---|---|
| run_stream_ns | data-model §Namespace scheme `agora:{run_id}:stream` | high |
| run_state_ns | data-model §Namespace scheme `agora:{run_id}:state` | high |
| run_events_ns | data-model §Namespace scheme `agora:{run_id}:events:stream` | high |
| agent_stream_ns | data-model §Namespace scheme `agora:{run_id}:{agent_id}:stream` | high |
| agent_state_ns | data-model §Namespace scheme `agora:{run_id}:{agent_id}:state` | high |

### A.3 原子 / 引擎 API / 事件

| symbol | origin | confidence |
|---|---|---|
| LLM.complete | atomic-relay §1 ① | high |
| render / parse / OutputSpec / Parsed | atomic-relay §1 ②③ | high |
| Selector / Selection | atomic-relay §1 ④ + SAD §4 选人原子 | high |
| Terminator / StopDecision | atomic-relay §1 ④ + SAD §4 判停原子 | high |
| StreamStore / StateStore | atomic-relay §1 ⑤ + data-model §Indexes access pattern | high |
| Summarizer | SAD §4 摘要原子（US-06 / AC-12） | medium |
| create_run | Flow 3（AC-02/02b） | high |
| resume_run | Flow 10（AC-15/15b） | high |
| relay | Flow 1（AC-01/05/08/09/10b，ADR-0007） | high |
| stop_run | Flow 8（AC-11） | high |
| read_transcript | Flow 12 读路径（AC-16/17 隔离内） | high |
| subscribe | Flow 11（AC-18） | high |
| register_capability | Flow 9（AC-14，ADR-0004/0005） | high |
| ProgressEvent / Observer | Flow 11 + SAD §8 Observability | high |
| run.turn_started / turn_landed / converged / stopped | SAD §8「回合开始/发言落桌/收敛/停止」 | high |

### A.4 CLI

| command / flag | origin | confidence |
|---|---|---|
| run --config | spec §1 配置=YAML + AC-02 | high |
| run --topic / --stance | data-model config.runtime.topic/stance（AC-02b） | high |
| stop | AC-11（Flow 8） | high |
| resume | AC-15（Flow 10） | high |
| observe | AC-18（Flow 11） | high |
| exit 0/1/2 | brainstorm `cli/__init__.py` 约定（镜像） | high |
| --db | brainstorm `cli/__init__.py` DEFAULT_DB（镜像，路径 `agora.db`） | medium |

## B. Drift checklist（4 点）

> 点 1–3 为核心；任一 ✗ 或合计 ≥3 旗标会暂停。点 4 为支撑，✗ 记后续。

1. **公开符号 ↔ data-model**（core）— **✓**。每个公开类型/函数映射到 data-model 实体（RUN/TURN/AGENT/PRIVATE_STATE 或 config 快照字段）或 atomic-relay 原子；无凭空字段。唯一低置信度为 `SummaryConfig`（见 §C-2）。
2. **错误码 ↔ 仓库错误登记**（core）— **✓**。契约 `agora.*` 已落地：`agora/errors.py` 登记 12 个错误码（§3 表）——前 9 个逐一对应 AC（AC-03/04/13/02b/15b/06 等），后 3 个为加载时校验类别（`reserved_agent_id`/`invalid_placeholder`/`invalid_config`）。无游离码。
3. **校验 ↔ 约束**（core）— **✓**。data-model 明示「无 DDL 约束，不变式在应用层强制（AC-02/03/04/13，ADR-0005）」；契约把 `max`/`window`/`output` 枚举、角色描述必填、能力 ∈ 菜单 ∪ 已注册扩展、output↔select/stop 匹配全部落在 `validate_config` 面（§6）。data-model 未给 `window`/`max` 数值上限 → 契约亦不写死（未发明约束）。
4. **契约 ↔ 序列**（supporting）— **✓**。§6 的 12 条 flow 均有对应公开入口：Flow 1→`relay`、Flow 2/3→`create_run`+`validate_config`、Flow 4→`Selector`、Flow 5→`Terminator`、Flow 6→`agora.turn_already_produced`、Flow 7→`Summarizer`、Flow 8→`stop_run`、Flow 9→`register_capability`、Flow 10→`resume_run`、Flow 11→`subscribe`/`Observer`、Flow 12→`read_transcript`+namespace 隔离。无孤儿 flow。

**结论**：4/4 ✓，无核心旗标。两条上游反哺缺口（§C）已在实现阶段收口（T23），无未决项。

## C. Back-feed（上游缺口，非 api 缺陷）

### C-1. ~~SAD 命名漂移：`session_id` → `run_id`~~（已收口，T23）

`data-model.md` 已把 Session/Speech/Persona 中性化为 **Run/Turn/Agent**、命名空间根为 `agora:{run_id}:*`；`sad.md` 的 `session_id` 残名已在实现阶段（T23）全部回改为 `run_id`，与 data-model/契约/代码一致。本条反哺项关闭。

### C-2. ~~`SummaryConfig` 形状未定义~~（已收口，T23）

`SummaryConfig` 已 ratify 为最小形状 `role`/`key`/`window`（`data-model.md` §RUN summary、`public-api.md` §2.1、`agora/types.py` 三处一致）。摘要原子（US-06 / AC-12）的配置输入结构已明确。本条反哺项关闭。

## D. 约定与默认

- 界面种类按 `sad.md` frontmatter `target_surfaces` **读取**（未重派生）：`library-sdk` → `contracts/public-api.md`、`cli` → `contracts/cli.md`。
- 错误信封 `{code, message, details?}`，`code` 中性 `agora.*` snake_case（SAD §2/§8，取代 `session.*`）。
- 无 OpenAPI（无 backend-service）、无 `events.md`（无 worker 表面；进度事件进程内、无幂等/重试/死信，SAD §6 flagged items）。
- `info.version`/包版本 `0.1.0` 不静默推进；由 CHANGELOG 显式 bump。
