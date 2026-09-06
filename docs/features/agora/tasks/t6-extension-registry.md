---
id: T6
title: "实现扩展区注册（register_capability）"
layer: "app"
deps: ["T2"]
acs: ["AC-14"]
files_hint: ["agora/extension.py"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T6 — 实现扩展区注册（register_capability）

## Why

菜单之外的自定义能力走受控扩展区（[ADR-0004](../adr/0004-provide-controlled-extension-zone.md)），独立于标准菜单、接口风格可自定义、本轮不承诺稳定/版本化。来源：[public-api.md §4 扩展区](../contracts/public-api.md) + [sad.md §6 Flow 9](../sad.md)。

## What

`agora/extension.py` 落地 `register_capability(registry, name, capability)`：

- registry 为 `dict[str, Any]`，登记自定义 selector/terminator/summarizer 等能力。
- 先注册、后加载（[ADR-0005](../adr/0005-validate-config-at-load-time.md)）：T5 的 `known_capabilities` = 菜单 ∪ registry 键；未注册即拒。
- 信任边界（ADR-0004）：同进程、视为受信代码，读范围以 AC-16/17 为界（不跨 namespace）。

## Definition of Done

- [ ] AC-14 单测全绿：注册一个自定义能力 → 场景引用它通过校验并生效；未注册引用被拒。
- [ ] 断言注册扩展能力后，标准菜单与引擎其余部分不受影响（回归现有菜单原子）。
- [ ] lint + mypy clean。

## Notes

- registry 是普通 `dict`，由 T11（wiring）创建并注入 T5 校验与 T7 接力；本任务不 import config/relay，保持与 T5 并行。
- 扩展区 ABI 本轮不承诺稳定/版本化（ADR-0004 后果），代码注释标注「内部逃生门」。
