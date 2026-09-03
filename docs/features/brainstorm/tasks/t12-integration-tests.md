---
id: T12
title: "集成 / 并发 / 耐久测试与 NFR 插桩验证"
layer: "tests"
deps: ["T11", "T9", "T10"]
acs: []
files_hint: ["tests/"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T12 — 集成 / 并发 / 耐久测试与 NFR 插桩验证

## Why

[spec §6 NFR](../spec.md)（并发 ≥5、可靠性 99.9%、0 丢失/重复、延迟 p95）与 [sad §10 质量场景](../sad.md)（QG-1/2）需要跨层测试与插桩，无法塞进单任务单测。派生自 [sad §7 监控](../sad.md)（`turn_overhead_p95_ms` / `table_read_p95_ms` / `session_token_usage`）。

## What

- 并发测试：≥5 会话并行不串扰（ADR-0005 每会话独立实例）。
- 耐久测试：进程崩溃 / LLM 失败 / 超时后 `resume_session` 恢复、已落桌不重放（ADR-0003）。
- 不变量测试：追加顺序 0 丢失/重复。
- 插桩：回合编排开销 p95、读桌面 p95、每会话 token 用量。

## Definition of Done

- [ ] 并发测试：≥5 会话互不串扰（spec §6 并发 NFR）
- [ ] 耐久测试：进程崩溃 / LLM 失败 / 超时后可恢复、已落桌不重放（QG-2）
- [ ] 不变量测试：每场会话 0 丢失/重复发言（QG-1）
- [ ] 插桩验证：`turn_overhead_p95` ≤100ms、`table_read_p95` ≤50ms（spec §6 延迟）

## Notes

- 依赖 T11（CLI 全链路）+ T9/T10（全部停止/收敛路径）就绪后跑端到端。
- 并发测试用每会话独立 weave 实例（ADR-0005）+ 单 SQLite 文件 WAL；耐久测试用 FakeLLM 注入失败/超时。
