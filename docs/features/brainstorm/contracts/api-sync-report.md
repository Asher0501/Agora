---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
---

# API sync report — brainstorm

> 表面 `[library-sdk, cli]`（sad frontmatter）→ 契约形式 `contracts/public-api.md` + `contracts/cli.md`（**非** HTTP/OpenAPI，无 backend-service 表面）。本报告沿用漂移检查纪律（field-origins 表 + 4 点清单 + 反向覆盖核查），字段溯源对象为 `data-model.md`（**存在**，且声明「no schema change」复用 weave `memory_entries`——非 fast-lane skip，直接派生）。

## Section A — field-origins

| contract element | origin | confidence |
|---|---|---|
| `create_session.config.topic` | `data-model` SESSION.topic（非空） | high |
| `create_session.config.personas` | `data-model` SESSION.personas | high |
| `create_session.config.scheduler` | `data-model` SESSION.scheduler | high |
| `create_session.config.stop_condition` | `data-model` SESSION.stop_condition | high |
| `create_session.return.session_id` | `data-model` SESSION.session_id | high |
| `PersonaConfig.persona_id` | `data-model` PERSONA_INSTANCE.persona_id | high |
| `PersonaConfig.name` | `data-model` SESSION.config.personas[].name | high |
| `PersonaConfig.role_description` | `data-model` PERSONA_INSTANCE.role_description（AC-13 必填） | high |
| `StopConditionConfig.type` | `data-model` stop_condition.type（枚举） | high |
| `StopConditionConfig.max_speeches` | `data-model` stop_condition.max_speeches | high |
| `run_session.session_id` | `data-model` SESSION.session_id | high |
| `run_session.return.speeches[]` | `data-model` SPEECH（升序） | high |
| `run_session.return.converged` | `data-model` SESSION.conclusion.converged | high |
| `run_session.return.conclusion` | `data-model` SESSION.conclusion.conclusion | high |
| `read_table.return[].seq` | `data-model` SPEECH.seq | high |
| `read_table.return[].speaker_id` | `data-model` SPEECH.speaker_id | high |
| `read_table.return[].text` | `data-model` SPEECH.text | high |
| `read_table.return[].created_at` | `data-model` SPEECH.created_at | high |
| `resume_session.session_id` | `data-model` SESSION.session_id（ADR-0003） | high |
| `stop_session.session_id` | `data-model` SESSION.session_id | high |
| `Role.speak` → `RoleContext.private_memory` | `data-model` PRIVATE_MEMORY（ADR-0006） | medium |
| `session.topic_required` | `spec` AC-02 | high（spec 派生，无 repo 注册表） |
| `session.insufficient_personas` | `spec` AC-03 | high |
| `session.persona_role_required` | `spec` AC-13 | high |
| `session.round_quota_exhausted` | `spec` AC-15 | high |
| `session.not_found` | 无来源（推断） | **low** |
| `session.invalid_state` | 无来源（推断） | **low** |
| `cli create --topic / --personas / --scheduler / --stop-condition / --max-speeches / --config` | 映射 `SessionConfig` / `StopConditionConfig` | high |
| `cli export --format` | 派生（输出格式约定） | high |

## Section B — drift findings（4 点清单）

1. **Operation ↔ data-model（core）** ✓ — 每个操作读写 ≥1 实体：`create_session`→SESSION；`run_session`→SESSION+SPEECH+SESSION.conclusion；`read_table`→SPEECH；`stop_session`→SESSION.status；`resume_session`→SESSION；注册操作→扩展注册表（ADR-0002 内核）。
2. **Error code ↔ repo error definition（core）** ✓（记录，非失败）— `14_forum` 为全新工程，**无错误注册表**。4 个 AC 派生的 `code` 为契约提案，待 `implement` 落地为真实错误定义；2 个 `# inferred` 见第 4 点。跨会话隔离（AC-06/06b）为 namespace 构造保证，无运行时错误码。
3. **Validation ↔ constraint（core）** ✓ — `topic` 非空（AC-02）、`personas` 去重后 ≥2（AC-03）、`role_description` 必填（AC-13）、`scheduler` 枚举 `round_robin|moderator`、`stop_condition.type` 枚举 `fixed_rounds|convergence|manual`、`seq` 严格单调（AC-05 不变量）——契约与 `data-model` 一致，无冲突。
4. **Contract ↔ sequence（supporting）** ✓（含 2 个序列缺口）— 每个 §6 流程映射到一个操作/结果（见下）；但「对不存在 / 已结束的会话操作」没有任何 §6 分支覆盖 → 契约的 `session.not_found` / `session.invalid_state` 无序列来源。此为**上游缺口**（非 api bug），见下方 OQ。

## Back-feed — coverage cross-check

### §5 AC → 操作映射（20/20 ✓）

| AC | 操作 / 结果 |
|---|---|
| AC-01·02·03·13 | `create_session` |
| AC-04·04b·15 | `run_session`（04b=跳过记录、15=round_quota_exhausted） |
| AC-05 | `read_table` |
| AC-06 | `run_session` / namespace 写隔离 |
| AC-06b | `read_table` / namespace 读隔离 |
| AC-07·07b·08 | `run_session`（moderator 调度；07b=回退+记录） |
| AC-09·10·10b | `run_session`（三种停止结果） |
| AC-11·11b | `stop_session`（11b=在途发言等待落桌） |
| AC-12 | `create_session`（新配置即新会话） |
| AC-14 | `register_role / register_scheduler / register_stop_condition / register_consumer` |

### §6 alt 分支 → 错误 / 结果映射

| 流程 | alt 分支 | 契约落点 |
|---|---|---|
| 启动会话（F2） | 主题为空 / 人设不足 / 缺角色描述 | `session.topic_required` / `insufficient_personas` / `persona_role_required` |
| 接力发言（F3） | 本轮已发言 / 生成失败 | `round_quota_exhausted` / 跳过（系统事件） |
| 共享桌面（F4） | 越界写入 / 越界读取 | 构造隔离（namespace 保证，无运行时错误码） |
| 路由者调度（F5） | 收敛 / 无效选择 | `SessionOutcome.converged` / 回退+记录（系统事件） |
| 自动停止（F6） | 固定轮数 / 收敛 / 上限兜底 | `SessionOutcome` 三种结果 |
| 手动停止（F7） | 在途发言 | `stop_session` 等待落桌语义 |
| 配置与扩展（F8） | — | `register_*` + `create_session(config)` |

### 序列缺口（Open Questions，owner 为上游阶段）

- **OQ-1（owner: `sequences`）**：spec §5 与 sad §6 均未覆盖「对不存在的 session_id 操作」（`not_found`）与「对已停止会话 run/stop」（`invalid_state`），以及「发起人如何重新发现一个待恢复的 session_id」（resume 的发现路径）。契约暂以 `# inferred` 低置信度包含两个错误码。**due: before contract finalized**。
- **OQ-2（owner: `specify`）**：ADR-0006（人设私有记忆）为 critic 阶段的 Decision override，但未回灌 spec §4 用户故事 / §5 AC——`PRIVATE_MEMORY` 实体在契约中仅作为 `RoleContext.private_memory` 扩展能力出现，无覆盖它的验收标准。契约以 `# inferred` 保留该能力。**due: before contract finalized**。

## Resolution

核心点 1–3 全 ✓；第 4 点为 supporting 级序列缺口（记 OQ，非 api bug）；flags 共 2 个（<3），**不暂停**。2 个 OQ 已记录（owner 分别为 sequences / specify），不修改上游源文件（本技能不编辑 source）。
