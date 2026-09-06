---
id: T7
title: "实现接力循环（选人→判停→产出→落桌）"
layer: "app"
deps: ["T2", "T3", "T4", "T6"]
acs: ["AC-05", "AC-06", "AC-07", "AC-07b", "AC-08", "AC-09", "AC-10b", "AC-18"]
files_hint: ["agora/relay.py"]
owner: "Asher"
estimate: "L"
status: "todo"
---

# T7 — 实现接力循环（选人→判停→产出→落桌）

## Why

引擎的核心编排（[ADR-0007](../adr/0007-check-stop-before-producing-each-turn.md)）：每轮 `选人 → 判停 →（未停才）产出 → 落桌`。这是 AC-05/06/07/07b/08/09/10b/18 的行为落点，也是 `relay` 公开入口（[public-api.md §5](../contracts/public-api.md)）。来源：[sad.md §6 Flow 1/4/5/6](../sad.md)。

## What

`agora/relay.py` 落地 `relay(repository, registry, run_id) -> RunOutcome`，循环：

1. **选人**：按 `SelectConfig.type` 调 `round_robin` 或 `llm_pick`；`Selection.invalid_choice` 非空 → 重试 1 次，仍无效 → 回退 roster 顺序，每次无效写 `agora:{run_id}:events:stream` 观测事件（AC-07b，sad §8）。
2. **判停**（产出前，ADR-0007）：`fixed_rounds` 数条数 / `llm_verdict` 轮首调 judge（解析失败 → 视为未收敛 + 观测事件）/ `manual` 查停止标志；汇总为 `StopDecision`（含 `termination`）。
3. **产出**：未停才调角色产出（render + LLM + parse），标注 `agent_id` 追加到转录，`seq` 单调递增（AC-05）。
4. **落桌 + 每 turn 恰好一条**：同一 turn 二次产出被阻止（AC-06 → `agora.turn_already_produced`）。
5. **终止产物**：收敛（AC-08）写 `verdict` + `recap`；达固定条数（AC-09）不额外多产；达上限未收敛（AC-10b）写「未收敛」`recap`。
6. **进度事件**（AC-18）：`run.turn_started`/`turn_landed`/`converged`/`stopped` 只携带本 run 内容。

## Definition of Done

- [ ] 接力循环单测全绿：AC-05（按序落桌标注发言者）、AC-06（同 turn 二次产出被拒）、AC-07（选人路由）、AC-07b（无效重试 + 回退 + 观测事件）、AC-08（裁判收敛写 verdict+recap）、AC-09（固定条数不多产一条）、AC-10b（上限未收敛标注未收敛）。
- [ ] 进度事件单测全绿：事件 payload 只含本 run 内容，不含他会话转录摘录/私有状态（AC-18）。
- [ ] 追加顺序不变量：`seq` 严格单调、无丢失/重复。
- [ ] lint + mypy clean。

## Notes

- **引擎无语义边界**（sad §4 内联）：不得加「自选自判」「选人反复点中同一角色」这类结构校验——留给场景作者在 prompt 约束（spec §8 OQ1）。
- `manual` 判停查停止标志：停止标志由 T8 `stop_run` 写入 run state（本任务只读、不写）；两者经 run state 协作，不 import 彼此。
- 与 T9（摘要钩子）、T8（停止/恢复协作）共享 `relay.py`/run state 概念；T9 会扩展本文件的产出步骤（见其 files_hint 重叠）。
- 与 T8 并行可开发，但 T10（CLI）需两者都就绪。
