---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0004 — Orchestrate turns synchronously; use the event bus for observability only

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk）

## Context

回合接力是天然同步的：下一位发言者依赖上一条发言的内容与顺序。但 weave 提供了进程内 `event_bus`（异步 pub/sub），未来消费界面（Web 论坛、观察者角色）会想要「实时」进度。需要决定：回合推进的控制流走同步调用还是事件驱动。

## Decision drivers

- §1 质量目标：一致性/耐久（0 丢失/重复，追加顺序不变量）。
- spec §2 Goal：引擎与界面解耦，未来消费界面经扩展点接入。
- §4 种子：共享桌面作为单一事实来源（顺序是核心不变量）。

## Considered options

1. **同步编排 + 事件仅观测** — 控制流同步进程内调用；event_bus 只发进度事件。
2. **事件驱动控制流** — event_bus 承载回合推进（发言落桌 → 发事件 → 调度器订阅后推进）。

## Decision outcome

**Chosen:** 同步编排 + 事件仅观测。回合推进（选下一发言者 → 调角色生成 → 追加共享桌面 → 判停止）走同步进程内调用，保证追加顺序与失败语义直观；`event_bus` 只发进度事件（回合开始 / 发言落桌 / 收敛 / 停止），供观测者与未来 UI 订阅，不承载控制流。

## Consequences

**Positive**
- 顺序不变量（0 丢失/重复、append-only）在同步控制流里最易保证与测试。
- 失败模型简单：一次发言失败 = 该回合的重试/跳过分支（AC-04b），不引入事件丢失/乱序问题。

**Negative**
- 未来「真·异步」需求（如后台多会话独立推进）仍需自己编排，事件化不会自动获得。
- 消费方不能仅靠订阅事件驱动引擎——事件只是只读的进度镜像。

**Neutral**
- event_bus 是进程内的；跨进程实时推送（WebSocket 等）是未来接前端时的新决策，不在本迭代。

## Links

- Spec: [[../spec.md]]
- SAD: [[../sad.md]] §4
