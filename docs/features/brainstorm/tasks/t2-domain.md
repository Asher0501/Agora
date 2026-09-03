---
id: T2
title: "定义领域类型、错误哨兵与四个扩展点协议（零 weave 依赖）"
layer: "domain"
deps: ["T1"]
acs: ["AC-02", "AC-03", "AC-13"]
files_hint: ["brainstorm/business/"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T2 — 定义领域类型、错误哨兵与四个扩展点协议

## Why

`business/` 是纯领域层，承载 [data-model.md](../data-model.md) 实体的类型化映射与 [public-api.md §2](../contracts/public-api.md) 的领域类型/扩展点协议。它是后续所有层的**契约任务**（T3–T10 都 import 它）。派生自 [sad §5 分层](../sad.md)「business 零 weave」与 [ADR-0002](../adr/0002-minimal-kernel-pluggable-extensions.md)「扩展点是接口」。

## What

- 领域类型（对齐 `public-api.md` §2 / `data-model.md` 实体）：`SessionConfig`、`PersonaConfig`、`SchedulerKind`、`StopConditionConfig`、`StopConditionKind`、`Session`、`SessionStatus`、`Speech`、`SessionOutcome`。
- 错误哨兵信封 `{code, message, details?}` + 6 个 AC 派生错误码（`session.topic_required` / `insufficient_personas` / `persona_role_required` / `round_quota_exhausted` / `cross_session_write` / `cross_session_read`）与 2 个 `# inferred`（`not_found` / `invalid_state`），见 `public-api.md` §5。
- `validate_config(config)`：AC-02/03/13 三项不变式。
- 四个扩展点协议 + 上下文类型（`public-api.md` §4）：`Role.speak`、`Scheduler.next_speaker`、`StopCondition.evaluate`、`Consumer.on_event`，及 `RoleContext` / `SchedulerContext` / `StopConditionContext` / `ProgressEvent`。
- namespace/键构建纯函数（`brainstorm:{sid}:stream|state`、`persona:{sid}:{pid}:*`、`brainstorm:{sid}:events`），见 [sad §8 命名空间](../sad.md)。

## Definition of Done

- [ ] 单元测试：`validate_config` 对空主题抛 `session.topic_required`（AC-02）、去重后 <2 抛 `session.insufficient_personas`（AC-03）、缺 `role_description` 抛 `session.persona_role_required`（AC-13）
- [ ] 四协议 + 上下文类型可导入，签名与 [contracts/public-api.md §4](../contracts/public-api.md) 一致
- [ ] `grep -r "import weave" brainstorm/business` 为空（零 weave 依赖）

## Notes

- 本任务是**契约任务**：T3–T10 均依赖其类型与协议。Python 无编译期耦合，故不设 compile-coupled lane——但 T2 必须先行，deps 已覆盖。
- 2 个 `# inferred` 错误码（`not_found`/`invalid_state`）为 [api-sync-report OQ-1](../contracts/api-sync-report.md) 的序列缺口，按契约提案落地；上游已记 OQ（owner: sequences），本任务不解决。
- **De-scope 注（review 后）**：`cross_session_write/read` 两码已删除（隔离由 namespace 构造保证，spec AC-06/06b 改为「构造隔离」）；`brainstorm:{sid}:events` 落点改为 `:events:stream`（weave 约束）。上文「6 个 AC 派生错误码」与 `:events` 是 T2 当时的契约提案，现以 `public-api.md` §5（4 码）与 `data-model.md` §System records（`:events:stream`）为准。
