---
id: T7
title: "实现引擎生命周期与扩展注册表：create / read / resume / register"
layer: "app"
deps: ["T2", "T3"]
acs: ["AC-01", "AC-02", "AC-03", "AC-05", "AC-06b", "AC-13", "AC-14"]
files_hint: ["brainstorm/engine/registry.py", "brainstorm/engine/session.py", "brainstorm/engine/table.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T7 — 实现引擎生命周期与扩展注册表

## Why

[ADR-0002](../adr/0002-minimal-kernel-pluggable-extensions.md) 内核四样中，会话生命周期、共享桌面、扩展注册表在此落地（回合循环在 T8）。公开操作对应 [public-api.md §3](../contracts/public-api.md)：`create_session` / `read_table` / `resume_session` + 四个 `register_*`。

## What

- `engine/registry.py`：`register_role/scheduler/stop_condition/consumer` + 取回。
- `engine/session.py`：`create_session`（校验 → 落盘 `config` → 返回 Session）、`resume_session`（从落盘状态重建，ADR-0003 恢复语义）。
- `engine/table.py`：`read_table`（按 namespace 读共享桌面，seq 升序，越界读拒绝）。

## Definition of Done

- [ ] 测试：`create_session` 校验通过后落盘并返回 Session（AC-01），校验失败抛对应错误（AC-02/03/13）
- [ ] 测试：`read_table` 按 namespace 返回有序发言（AC-05），越界读拒绝（AC-06b）
- [ ] 测试：`resume_session` 从落盘状态重建会话（恢复语义）
- [ ] 测试：`register_role/scheduler/stop_condition/consumer` 注册后可从注册表取回（AC-14 注册侧）

## Notes

- `stop_session`（含在途安全）不在本任务——归 T10。`run_session` 循环归 T8。
- 隔离由 namespace 承载：`read_table` 只带本会话 namespace，越界即拒绝（[sad §8](../sad.md)、spec §6.1）。
