---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0005 — Give each session its own Weave instance

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk）

## Context

spec §6 并发 NFR「并发会话数 ≥ 5 个会话互不串扰」。brownfield 扫描发现：单个 `Weave` 实例内部用 `asyncio.Lock` 串行化 `arun()`，且共享 `_active_scopes`、`_system_prompt` 等可变状态（`weave/agent.py:372-380`）——一个实例跑多个会话实际是排队，不是并发。需要决定每会话的隔离模型。

## Decision drivers

- spec §6 NFR：≥5 会话互不串扰。
- spec §6.1：会话之间按命名空间隔离（跨会话读写被拒绝）。
- §1 质量目标：会话可靠性 + 一致性。

## Considered options

1. **每会话独立实例** — 每个会话一个独立 Weave 实例，会话作为独立 async 任务并发。
2. **单共享实例串行** — 一个实例跑所有会话，会话在锁上排队。

## Decision outcome

**Chosen:** 每会话独立实例。每个会话构造自己的 `Weave(config, llm=…, loop=…)`，独立持有 `_active_scopes` / loop / LLM / 记忆状态；会话作为独立 async 任务并发运行；共享同一 SQLite 文件，靠 WAL 模式（多读者 + 单写者）安全承载并发读写。会话隔离由「每实例独立作用域激活」+「session 级 namespace」共同保证。

## Consequences

**Positive**
- 兑现 ≥5 会话互不串扰的并发 NFR，会话间无锁争用、无状态串扰。
- 会话隔离（§6.1）天然成立：每实例作用域互不可见，跨会话读写被 namespace 拒绝。

**Negative**
- 内存随会话数线性增长（每会话一套 loop/LLM/记忆对象）。
- 需要显式的生命周期管理：会话结束要正确 `close()` 其记忆后端，避免 SQLite 连接泄漏。

**Neutral**
- 「每会话一实例」确立了隔离边界；若未来会话数暴增到数十量级，需再评估进程池/多进程方案（§7）。

## Links

- Spec: [[../spec.md]]
- SAD: [[../sad.md]] §4
