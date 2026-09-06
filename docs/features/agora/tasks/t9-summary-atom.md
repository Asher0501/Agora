---
id: T9
title: "实现摘要原子与跨轮连续性"
layer: "app"
deps: ["T2", "T5", "T7"]
acs: ["AC-12"]
files_hint: ["agora/atoms.py", "agora/relay.py", "agora/config/schema.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T9 — 实现摘要原子与跨轮连续性

## Why

US-06「角色维持跨轮连续性」：摘要原子把共享转录压缩进角色私有状态，后续发言据此引用（AC-12，[ADR-0003](../adr/0003-replace-extension-protocols-with-five-atom-menu.md) 的第五原子）。来源：[sad.md §6 Flow 7](../sad.md) + [public-api.md §4 ⑥](../contracts/public-api.md)。

## What

三处扩展（本任务改 T2/T5/T7 的产物，故 files_hint 与之重叠 → 串行 lane）：

- `agora/atoms.py`：实现 `Summarizer` 的默认实例（last-N window 截断/拼接，可换 LLM 压缩）。
- `agora/config/schema.py`：把 `SummaryConfig` 最小形状（`role`/`key`/`window`，T1 落位）纳入解析与校验。
- `agora/relay.py`：产出步骤前，若角色配置了 summary → 压缩共享转录 → 写 `agora:{run_id}:{agent_id}:state[key]` → 注入该角色后续发言的 prompt（Flow 7，AC-12）。

## Definition of Done

- [ ] AC-12 单测全绿：配置了 summary 的角色在轮到时读到自己的摘要并据此产出（跨轮连续性成立）。
- [ ] 私有状态写入 `agora:{run_id}:{agent_id}:state`，按角色/会话 namespace 隔离（他人不可见）。
- [ ] `SummaryConfig` 最小形状被 `validate_config` 校验（缺 role/key 即拒）。
- [ ] lint + mypy clean。

## Notes

- **上游缺口（api-sync-report §C-2）**：`SummaryConfig` 字段级形状 data-model 未定义。本任务采用**最小形状 `role`/`key`/`window`** 并注释「待 data-model ratify」，不发明更宽字段；如需 LLM 摘要 prompt，作为 `key` 的私有状态内容处理，不新增配置段。
- 与 T2/T5/T7 共享文件（`atoms.py`/`schema.py`/`relay.py`），`implement` 按 files_hint 重叠串行化；本任务是接力循环的**增量**，不推翻 T7 已绿的循环行为。
