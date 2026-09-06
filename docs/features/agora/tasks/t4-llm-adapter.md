---
id: T4
title: "实现 LLM 适配（BaseLLM + FakeLLM）"
layer: "infra"
deps: ["T2"]
acs: []
files_hint: ["agora/adapter/llm.py"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T4 — 实现 LLM 适配（BaseLLM + FakeLLM）

## Why

LLM 是产出/选人/判停原子的能力来源（SAD §3「weave 框架 0.1.0，唯一集成点」）。`agora/adapter/llm.py` 把 weave 的 `BaseLLM` 适配到 T2 的 `LLM` 协议（`async complete(prompt) -> str`），并提供离线 `FakeLLM` 让后续测试不触网（spec §6 依赖可插拔 deepseek/anthropic/openai + 离线 FakeLLM）。

## What

- `agora/adapter/llm.py`：`BaseLLM` 适配 weave `BaseLLM`（deepseek/anthropic/openai 可插拔），满足 `LLM.complete`。
- `FakeLLM`：确定性输出（按 prompt 或固定序列返回），供 T7/T9 及全部测试离线使用。

## Definition of Done

- [ ] 单测断言 `FakeLLM` 输出确定性、不触网（无网络调用）。
- [ ] 适配类满足 `LLM` 协议（可被 T2 的 `llm_pick`/`llm_verdict`/产出消费）。
- [ ] lint + mypy clean。

## Notes

- 薄适配层；真实 deepseek/anthropic/openai 连通性不在本任务验收范围（依赖 weave，SAD §3）。
- `FakeLLM` 是 T7（接力循环）与 T14（回归测试）的离线测试前提，先落地。
