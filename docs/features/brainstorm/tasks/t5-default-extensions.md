---
id: T5
title: "实现默认扩展：round_robin 调度 + fixed_rounds 停止 + manual 停止"
layer: "app"
deps: ["T2"]
acs: ["AC-09"]
files_hint: ["brainstorm/extensions/schedulers/", "brainstorm/extensions/stop_conditions/"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T5 — 实现默认扩展（调度 + 停止）

## Why

[ADR-0002](../adr/0002-minimal-kernel-pluggable-extensions.md)：round-robin 调度、固定轮数停止、手动停止都是**默认扩展实现**，装配时注册，内核只认识「调度器」「停止条件」接口。这是三个纯逻辑默认实现，不含 LLM/持久化。

## What

- `extensions/schedulers/round_robin.py`：`next_speaker` 按固定顺序循环返回 persona_id。
- `extensions/stop_conditions/fixed_rounds.py`：按发言条数计（[spec §8 OQ](../spec.md) 默认），达 `max_speeches` 返回 Stop。
- `extensions/stop_conditions/manual.py`：收到停止指令前返回 Continue。

## Definition of Done

- [ ] 单元测试：`round_robin.next_speaker` 按固定顺序循环返回 persona_id
- [ ] 单元测试：`fixed_rounds.evaluate` 发言条数达 `max_speeches` 返回 Stop（AC-09 判定侧）
- [ ] 单元测试：`manual.evaluate` 在收到停止指令前返回 Continue

## Notes

- 这些实现只依赖 T2 的协议，与 T3/T4 并行。**不得**把策略逻辑写回 `engine/`（内核/扩展边界，spec §6 可扩展性 NFR）。
- 收敛停止条件（`convergence`）与路由者调度（`moderator`）不在本任务——留 T9（涉及 LLM 裁决）。
