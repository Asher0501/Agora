---
id: T10
title: "实现手动停止 stop_session：在途发言不丢失 + 产出 SessionOutcome"
layer: "app"
deps: ["T8"]
acs: ["AC-11", "AC-11b"]
files_hint: ["brainstorm/engine/stop.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T10 — 实现手动停止 stop_session

## Why

[spec §4 US-05](../spec.md)「发起人按停止条件结束会话」，其中手动停止是唯一由发起人即时触发的停止路径。派生自 [sad §6 F7](../sad.md) 与 [public-api.md §3](../contracts/public-api.md) `stop_session`。核心难点是在途发言不丢失（AC-11b）。

## What

- `engine/stop.py`：`stop_session(session_id)` 设置停止信号，等待在途生成落桌后结束。
- 产出 `SessionOutcome`（`converged` / `conclusion` / `speeches` 升序），对齐 `public-api.md §2 SessionOutcome`。

## Definition of Done

- [ ] 测试：手动停止立即结束并保留当前讨论记录（AC-11）
- [ ] 测试：停止时恰有在途生成 → 等待该发言落桌再结束（AC-11b）
- [ ] 测试：产出 `SessionOutcome`（`converged` / `conclusion` / `speeches`）完整

## Notes

- 在途等待语义（「落桌后结束」）与 T8 循环的生成路径协作；需一个共享的「在途发言」句柄，避免并发竞态（spec §6 一致性 NFR）。
- 与 T9 并行（都只依赖 T8），不同 `files_hint`，无重叠。
