---
id: T9
title: "实现路由者调度 + 收敛判定 + 无效选择回退 + 结论"
layer: "app"
deps: ["T8"]
acs: ["AC-07", "AC-07b", "AC-08", "AC-10", "AC-10b"]
files_hint: ["brainstorm/extensions/schedulers/moderator.py", "brainstorm/extensions/stop_conditions/convergence.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T9 — 实现路由者调度 + 收敛判定

## Why

路由者（Moderator）是可选调度策略，[spec §4 US-04](../spec.md)：每次发言后决定下一位并判断收敛。派生自 [sad §6 F5/F6](../sad.md) 与 [public-api.md §3](../contracts/public-api.md) `run_session` 的 moderator 分支。路由者本身是一个 LLM 角色（复用 T4 的生成能力）。

## What

- `extensions/schedulers/moderator.py`：路由者裁决下一位发言者；选定者不在名单内 → 回退 `round_robin` 并记录系统事件（AC-07b）。
- `extensions/stop_conditions/convergence.py`：路由者宣告收敛 → Stop；达 `max_speeches` 上限仍未收敛 → 强制 Stop 标注未收敛（AC-10b）。
- 收敛时写 `SESSION.conclusion`（converged + conclusion）。

## Definition of Done

- [ ] 测试：moderator 调度时路由者选定下一位发言者（AC-07）
- [ ] 测试：选定的发言者不在名单内 → 回退固定轮转并记录（AC-07b）
- [ ] 测试：路由者宣告收敛 → 会话结束并附结论（AC-08 / AC-10）
- [ ] 测试：达 `max_speeches` 上限仍未收敛 → 强制结束标注未收敛（AC-10b）

## Notes

- 「选谁」的约束由路由者人设描述表达，不硬编码在引擎内（AC-07）——moderator 实现只校验合法性 + 回退。
- 收敛草稿等路由者私有状态走 `persona:{sid}:{pid}:state`（ADR-0006，复用 T3 私有记忆）。
