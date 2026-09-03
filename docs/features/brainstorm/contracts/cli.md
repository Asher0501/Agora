---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
---

# CLI — brainstorm

> **契约来源（单向派生，非手写）：** 本文件是 `public-api.md`（引擎操作）+ `sad.md` §5 C4 Container「Brainstorm CLI」（创建/运行/停止会话、导出记录）+ `spec.md` §4/§5 的派生结果。CLI 是 library-sdk 的唯一对外入口（ADR-0001）；每个命令映射到一个引擎操作。

## Commands

入口命令 `brainstorm`。命令与引擎操作一一对应：

| command | 引擎操作 | US / AC |
|---|---|---|
| `brainstorm create` | `create_session` | US-01 / AC-01·02·03·13 |
| `brainstorm run <session-id>` | `run_session`（已存在未跑完 → `resume_session`） | US-02·03·04·05 / AC-04…AC-10b |
| `brainstorm stop <session-id>` | `stop_session` | US-05 / AC-11·11b |
| `brainstorm export <session-id>` | `read_table` | US-03 / AC-05 |

> `run` 对已存在但未跑完的会话等价于 `resume_session`（ADR-0003 恢复语义：恢复到中断那一轮，已落桌发言不重放）。
>
> `stop` 为 best-effort：它是独立进程，无法打断另一进程正在运行的 `run`、也无法等待其在途发言落桌。手动停止的完整语义（立即结束 + 在途发言不丢失，AC-11/11b）在 library-sdk 进程内成立；CLI `stop` 仅对已停止 / 未在运行的会话做收尾。

## Flags

### `brainstorm create`

| flag | 类型 | 必填 | 约束 | 映射 |
|---|---|---|---|---|
| `--topic <text>` | `str` | 是* | 非空（AC-02） | `SessionConfig.topic` |
| `--personas <file>` | path | 是* | YAML 名单，去重后 ≥2（AC-03） | `SessionConfig.personas` |
| `--scheduler <kind>` | `str` | 否 | `round_robin`\|`moderator`（默认 `round_robin`） | `SessionConfig.scheduler` |
| `--stop-condition <kind>` | `str` | 否 | `fixed_rounds`\|`convergence`\|`manual` | `StopConditionConfig.type` |
| `--max-speeches <n>` | `int` | 否 | `>0`（固定轮数 / 收敛兜底上限） | `StopConditionConfig.max_speeches` |
| `--config <file>` | path | 否 | YAML，覆盖以上单项 flag | 整体 `SessionConfig` |

`*` `--config` 与（`--topic` + `--personas`）二选一：`--config` 提供完整声明式配置（US-06 / AC-12，零硬编码）；单独 flag 供临时开一场。无论哪种来源，均走同一 AC-02/03/13 校验。

`--personas` / `--config` 中每项 persona 形如 `{persona_id, name, role_description}`，`role_description` 必填（AC-13）。

### `brainstorm run / stop / export`

| flag | 类型 | 必填 | 说明 |
|---|---|---|---|
| `<session-id>`（位置参数） | `str` (UUID) | 是 | 由 `create` 输出获得；`export` 亦可读入 `--format`（见下） |

`brainstorm export` 额外支持：

| flag | 类型 | 默认 | 说明 |
|---|---|---|---|
| `--format <fmt>` | `str` | `text` | `text`（逐条 `seq. speaker: text`）\| `json`（`Speech[]`） |

## Exit codes

| code | 含义 | 错误 `code`（若有） |
|---|---|---|
| `0` | 成功 | — |
| `2` | CLI 用法错误：未知命令/flag、缺必填参数、`--config` 与单项 flag 同时给出 | — |
| `1` | 领域拒绝 / 运行失败（映射 §错误 sentinel，`code` 随消息输出） | `session.topic_required`、`session.insufficient_personas`、`session.persona_role_required`、`session.round_quota_exhausted`、`session.not_found`*、`session.invalid_state`* |

`*` `# inferred`（见 `public-api.md` §5，序列缺口）。

## I/O 约定

- **stdout**：结果（`create` 打印 `session_id`；`export` 打印讨论记录；`run`/`stop` 打印 `SessionOutcome`）。
- **stderr**：错误消息 + `code`（领域拒绝）或用法提示（exit `2`）。
- `create` 输出的 `session_id` 是后续 `run`/`stop`/`export` 的输入（CLI 自身不持久化「最近会话」状态）。
