---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0006 — Give each persona private memory alongside the shared table

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk，critic 阶段）

## Context

spec §8 OQ1：「是否需要在全共享之外，为人设增加可选的私有便签/记忆？」默认「不需要，本迭代全共享」（owner: Tech Lead，due: before `sdd:design`）。设计评审（critic 阶段）中，用户明确要求保留「人设私有记忆」并作为本迭代真实能力——即人设除共享桌面外，还拥有彼此不可见的私有记忆/便签。

## Decision drivers

- 用户在设计评审中明确覆盖 spec §8 OQ1 默认，要求私有记忆本迭代就做。
- 人设可能需要在讨论之外持有私有工作记忆/便签（如路由者记录自己的收敛草稿）。

## Considered options

1. **全共享（无私有记忆）** — spec §8 OQ1 默认；人设只读共享桌面。
2. **共享桌面 + 私有记忆** — 每人设另有 `persona:{id}:*` 私有 namespace，他人不可见。

## Decision outcome

**Chosen:** 共享桌面 + 私有记忆。会话内共享桌面走 `brainstorm:{session_id}:stream`；每人设私有记忆走 `persona:{id}:stream|state`。两者同存于单一 SQLite 库（ADR-0003），按 namespace 隔离（§8 / spec §6.1）。

## Consequences

**Positive**
- 人设可持有私有便签（如路由者收敛草稿、个人待办），不污染共享讨论。
- 隔离模型清晰：会话共享（session 级）+ 人设私有（persona 级）两个层次。

**Negative**
- 比「全共享」多一个 namespace 维度，隔离/授权面更大（spec §6.1 需同时约束 persona 级与 session 级越界）。

**Neutral**
- 未来若判定私有记忆无用，移除 `persona:{id}:*` scope 即可（additive，可逆）。

## Links

- Spec: [[../spec.md]] §8 OQ1
- SAD: [[../sad.md]] §4
