---
id: T2
title: "定义五原子协议、产出/解析与闭集菜单原子"
layer: "domain"
deps: ["T1"]
acs: []
files_hint: ["agora/atoms.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T2 — 定义五原子协议、产出/解析与闭集菜单原子

## Why

闭集菜单的五个原子（[ADR-0003](../adr/0003-replace-extension-protocols-with-five-atom-menu.md)）是「已知能力」校验的锚点（[ADR-0005](../adr/0005-validate-config-at-load-time.md)），也是接力循环（T7）的组合原料。来源：[public-api.md §4](../contracts/public-api.md) + `atomic-relay.md` §1 ①–⑥。

## What

在 `agora/atoms.py` 落地（纯协议 + 纯函数 + 菜单原子，零 weave 依赖）：

- **六协议**：`LLM.complete`、`Selector.next`（返回 `Selection`）、`Terminator.should_stop`（返回 `StopDecision`）、`StreamStore.append/read`、`StateStore.get/set`、`Summarizer.summarize`。
- **产出/解析**：`render(template, ctx, window)`（注入字段 + 截断 history 到 window）、`OutputSpec`/`Parsed`、`parse(text, spec)`——三种输出语法：`free_text` 原文、`pick_next` 的 `NEXT:<id>|CONVERGE:<结论>`、`verdict` 的 `CONVERGE:<结论>|CONTINUE`；解析失败置 `parse_failure=True`（sad §8 OQ4 确定性回退的载体）。
- **五个菜单原子**：`round_robin`（按 roster 顺序轮转，正反交替=2 人轮转）、`llm_pick`（让某角色选下一位）、`fixed_rounds`（达 `max` 停，纯状态函数不调 LLM）、`llm_verdict`（某角色裁决 + `max` 兜底）、`manual`（查停止标志）。`Selection.invalid_choice` 字段承载 AC-07b 的无效选择。

## Definition of Done

- [ ] `parse` 单测覆盖三种输出格式 + 解析失败（`parse_failure=True`）+ `pick_next`/`verdict` 的 `CONVERGE` 命中/`NEXT` 命中，全绿。
- [ ] `render` 单测覆盖注入字段名 + `window` 截断条数。
- [ ] `round_robin`/`fixed_rounds` 为纯状态函数（不 import weave、不 import 任何 adapter），单测绿。
- [ ] `llm_pick`/`llm_verdict` 仅依赖 `LLM` 协议（依赖注入，可测）。
- [ ] lint + mypy clean。

## Notes

- `Selection.invalid_choice`、`Parsed.parse_failure`、`StopDecision.termination` 是 T7 接力循环消费的字段，先在此定义。
- 协议是 T3（Repository 实现 StreamStore/StateStore）、T4（LLM）、T6（扩展能力）的实现目标——后续任务 `implement` 它们。
