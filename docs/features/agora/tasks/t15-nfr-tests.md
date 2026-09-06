---
id: T15
title: "编写 NFR/一致性/并发测试"
layer: "tests"
deps: ["T11"]
acs: []
files_hint: ["tests/test_nfr.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T15 — 编写 NFR/一致性/并发测试

## Why

覆盖 spec §6 NFR 与 sad §10 QG-2/QG-4/QG-5：一致性/耐久（0 丢失/0 重复）、并发会话隔离（≥5）、编排/读延迟插桩。brainstorm 已有 `test_nfr.py`，迁移到 agora 语义并挂新指标名。

## What

`tests/test_nfr.py` 覆盖：

- **追加顺序不变量（QG-2，spec §6 一致性/耐久行）**：多角色多次追加后转录完整、有序、标注发言者，0 丢失/0 重复。
- **并发会话隔离（QG-5，spec §6 并发会话数行）**：≥5 会话并发运行，数据隔离断言（AC-16/17）+ 并发 p95 对比单会话不劣化超 2×。
- **延迟插桩（QG-4，spec §6 两行延迟）**：`turn_overhead_p95_ms`（每轮编排 p95，目标 ≤100ms）、`table_read_p95_ms`（读完整转录 p95，目标 ≤50ms）——本地插桩冒烟口径（sad §7 Monitoring 指标名）。

## Definition of Done

- [ ] 追加顺序不变量测试全绿（0 丢失/0 重复）。
- [ ] ≥5 并发会话隔离测试全绿（跨会话/角色越界不可见）。
- [ ] 延迟插桩跑通并记录 p95（冒烟口径；精确 ms 目标作为本地插桩基线，不硬断言 CI 绝对值）。
- [ ] lint + mypy clean。

## Notes

- 延迟目标（≤100ms/≤50ms）是**本地插桩基线**（spec §6「本地插桩」测量列），CI 上以「可运行 + 记录 + 不劣化」为门槛，不写死绝对 ms（避免 CI 抖动误报）。
- 会话可靠性（QG-3，≥99.9% 不被意外中断）是**耐久测试**口径，成本高、本任务以「恢复路径单测（T8 AC-15）+ 追加不变量」近似覆盖，长期耐久跑批留待集成环境。
