---
id: T4
title: "实现 PersonaRole 与 FakeLLM：经 weave 生成发言并注入上下文窗口"
layer: "infra"
deps: ["T2"]
acs: ["AC-04"]
files_hint: ["brainstorm/weave_adapter/persona_agent.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T4 — 实现 PersonaRole 与 FakeLLM

## Why

角色是 [ADR-0002](../adr/0002-minimal-kernel-pluggable-extensions.md) 的四个扩展点之一；默认 `Role` 实现（`PersonaRole`）经 weave 的 `BaseLLM` 生成发言，是 [sad §5](../sad.md)「weave_adapter 唯一集成点」的角色侧。离线测试用 `FakeLLM`（[sad §2](../sad.md)）。

## What

- `PersonaRole`：实现 `Role.speak(ctx)`，把 `RoleContext`（topic + 截断历史 + 私有记忆句柄）组装成 prompt 交 weave `BaseLLM` 生成发言。
- `FakeLLM`：离线返回固定/回显文本，供单测与后续 T8 循环测试。
- 上下文窗口注入：[sad §8](../sad.md)「截断到最近 N 条 + 可选摘要」，N 可配置。

## Definition of Done

- [ ] 单元测试（FakeLLM）：`Role.speak(ctx)` 返回针对主题、含历史发言窗口的文本（AC-04 生成侧）
- [ ] 上下文注入测试：历史被截断到最近 N 条（N 可配置）
- [ ] `RoleContext.private_memory` 句柄可读/写本人设私有记忆（ADR-0006）

## Notes

- 发言者由系统标注（`speaker_id` 来自人设 id），不以内容自称为准（spec §6.1 冒名发言防线）——本任务不信任 LLM 输出中的身份声明。
- 与 T3（repository）并行：两者都在 `weave_adapter/` 但不同文件（`repository.py` vs `persona_agent.py`），无 `files_hint` 重叠。
