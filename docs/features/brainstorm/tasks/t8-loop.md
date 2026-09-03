---
id: T8
title: "实现回合编排循环 run_session：选人 → 生成 → 落桌 → 判停"
layer: "app"
deps: ["T7", "T5", "T4"]
acs: ["AC-04", "AC-04b", "AC-09", "AC-14", "AC-15"]
files_hint: ["brainstorm/engine/loop.py"]
owner: "Asher"
estimate: "L"
status: "todo"
---

# T8 — 实现回合编排循环 run_session

## Why

回合循环是内核的心脏，也是 [ADR-0004](../adr/0004-sync-orchestration-events-observability.md)「同步编排」的载体：选下一发言者 → 调角色生成 → 追加共享桌面 → 判停止，全程同步进程内调用，event_bus 只发进度事件。派生自 [sad §6 F1/F3](../sad.md) 与 [public-api.md §3](../contracts/public-api.md) `run_session`。

## What

- `engine/loop.py`：`run_session(session_id)` 驱动回合循环至停止条件成立。
- 单轮名额：同一发言者本轮二次追加 → `session.round_quota_exhausted`（AC-15）。
- 生成失败：重试 N 次仍失败 → 跳过并记录系统事件（`brainstorm:{sid}:events`，AC-04b）。
- 进度事件：`session.turn_started` / `session.speech_landed` / `session.stopped` 按序发（ADR-0004）。

## Definition of Done

- [ ] 测试：happy path 跑满固定轮数结束，桌面含按序发言（AC-04 / AC-09）
- [ ] 测试：生成失败重试 N 次仍失败则跳过并记录系统事件，会话继续推进（AC-04b）
- [ ] 测试：单轮内同一发言者二次追加被拒 `round_quota_exhausted`（AC-15）
- [ ] 测试：进度事件按 `turn_started` / `speech_landed` / `stopped` 顺序发出（ADR-0004）

## Notes

- 失败语义的具体参数（重试次数 N、退避）为 [sad §11 已接受债务](../sad.md)，本任务按 AC-04b 形状实现，参数留配置。
- 路由者调度（AC-07/07b/08）与收敛停止（AC-10/10b）不在本任务——归 T9；手动停止（AC-11/11b）归 T10。
