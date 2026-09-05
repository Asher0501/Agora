---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0006 — Resume sessions from a creation-time config snapshot

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

会话崩溃后恢复（AC-15）时，会话应按「创建时快照的配置」还是「恢复时实时读的配置」运行？这是 spec §8 OQ3。

## Decision drivers

- 会话可靠性（top-3 质量目标）——恢复等于从断点继续，规则不应中途变化。
- spec §8 OQ3 默认——快照（创建时定格），避免崩溃后改配置导致半程规则变化。

## Considered options

1. **创建时快照** — 启动时把 YAML 配置定格存进会话 state，resume 读快照。
2. **恢复时实时读** — 被否：半程改配置会导致同一场会话前后选人/判停/角色名单不一致。

## Decision outcome

**Chosen:** Option 1. 会话创建时把配置快照写入会话状态（state），resume 一律按快照运行，不重读磁盘配置。

## Consequences

**Positive**
- 崩溃恢复前后规则一致，resume 语义清晰。

**Negative**
- 每场会话多一份配置快照存储。

**Neutral**
- 改配置只影响新会话，不影响在途/已中断会话。

## Links

- Spec: [[../spec.md]] §8/§5 AC-15
- SAD: [[../sad.md]] §4/§5
- Related ADR: [[0007-check-stop-before-producing-each-turn]]
