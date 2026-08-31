---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0003 — Persist sessions in a single SQLite store with resume-at-round

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk）

## Context

spec §8 OQ：「会话是否需要跨进程/跨重启持久化？若持久化，恢复语义如何？」默认「是，恢复到中断那一轮、已落桌发言不重放」。§6 会话可靠性 NFR「已开始的会话 99.9% 不被意外中断」+ 一致性 NFR「每场会话 0 条丢失或重复发言」。需要决定存储形态：持久化到哪里、如何隔离、如何恢复。

## Decision drivers

- spec §8 OQ 默认：持久化，恢复到中断那一轮，已落桌发言不重放。
- spec §6 NFR：0 丢失/重复发言（追加顺序不变量）+ 99.9% 会话可靠性。
- §2 Constraint：沿用 demo 的 SQLite + namespace 隔离机制。
- spec §6.1：会话之间按命名空间隔离。

## Considered options

1. **单库持久化 + 会话级 namespace + 可恢复** — 单一 SQLite 库，`brainstorm:{session_id}:stream|state` 隔离，发言落盘即追加，崩溃恢复到中断那一轮。
2. **仅内存，不持久化** — 会话随进程结束即丢。

## Decision outcome

**Chosen:** 单库持久化 + 会话级 namespace + 可恢复。单一 SQLite 文件（沿用 demo `memory.db` 的 `memory_entries` 表 + namespace 隔离），每个会话一个 `brainstorm:{session_id}` 作用域，发言以带顺序号的流条目追加；恢复时重放已落桌的流（不重放发言），从「下一个待发言者」那一轮继续。

## Consequences

**Positive**
- 兑现 99.9% 会话可靠性 + 0 丢失/重复两个 NFR：发言落盘即持久，崩溃/重启可恢复。
- 会话隔离天然由 namespace 承载（spec §6.1），跨会话读写被拒绝。

**Negative**
- 比纯内存多一层持久化读写；恢复逻辑（哪些算「已落桌、哪些是进行中」）需要明确的状态机。
- SQLite 单文件并发写有上限（WAL 模式下读并发 + 单写者），极端并发需另议（§7）。

**Neutral**
- 恢复语义「恢复到中断那一轮、已落桌不重放」是本次锁定的精确语义，未来若要「断点续生成」需另立 ADR。

## Links

- Spec: [[../spec.md]]
- SAD: [[../sad.md]] §4
