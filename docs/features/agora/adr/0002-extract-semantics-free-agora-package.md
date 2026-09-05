---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0002 — Extract the kernel into a new semantics-free `agora/` package

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

brainstorm 的语义泄漏在五处（explorer 定位）：领域类型（Session/Speech/Persona）、字面量枚举（SchedulerKind/StopConditionKind）、`brainstorm:`/`persona:` 命名空间根、中文错误消息、`session.*` 错误码。要把内核抽成无语义引擎，需决定包的切法。

## Decision drivers

- spec §2「引擎与场景语义解耦」——内核不得携带任何场景词汇。
- 一致性/耐久（top-3 质量目标）——命名空间/错误码是隔离与恢复的载体，必须中性化。
- 破坏性变更被允许（spec §3「不迁移旧会话数据」）。

## Considered options

1. **新建中性 `agora/` 包** — 类型/命名空间/错误码全部中性化，brainstorm 迁移为第一个场景配置。
2. **就地重构 `brainstorm/`** — 在包内抽 `core/` 子包 + 薄 brainstorm 层。被否：`core/` 仍带 brainstorm 痕迹，「无语义」不彻底。

## Decision outcome

**Chosen:** Option 1. 新建 `agora/` 包；brainstorm 的领域类型、命名空间、错误码、CLI 全部重写为中性形式，并以「场景」身份回归其 58 个测试。

## Consequences

**Positive**
- 内核零 brainstorm 语义，辩论/面试等新场景不会在残留语义上打转。
- brainstorm 测试回归成为「零代码扩展成立」的实证（AC-01）。

**Negative**
- 一次破坏性重构，brainstorm 的类型/命名空间/错误码/CLI 均需改写。
- 旧 brainstorm 会话数据不迁移（spec §3 已允许）。

**Neutral**
- 迁移完成前需同时维护 brainstorm 旧包与 agora 新包。

## Links

- Spec: [[../spec.md]] §1/§3
- SAD: [[../sad.md]] §4/§5
- Related ADR: [[0003-replace-extension-protocols-with-five-atom-menu]]
