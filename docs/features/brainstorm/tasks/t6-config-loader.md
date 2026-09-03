---
id: T6
title: "实现声明式 YAML 配置加载与默认装配（零硬编码）"
layer: "wiring"
deps: ["T2"]
acs: ["AC-12", "AC-13", "AC-14"]
files_hint: ["brainstorm/config_loader.py", "brainstorm/wiring.py"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T6 — 实现声明式 YAML 配置加载与默认装配

## Why

[spec §6 US-06](../spec.md)「声明式配置改动人设/调度/停止条件，无需改代码」与 [sad §2 约定](../sad.md)「配置全部来自 YAML、零硬编码」。本任务把 YAML 解析为 `SessionConfig`，并把默认扩展装配进引擎（composition/DI），是 [ADR-0002](../adr/0002-minimal-kernel-pluggable-extensions.md)「装配时注册默认实现」的落点。

## What

- `config_loader.py`：YAML（人设名单 + 调度 + 停止条件）→ `SessionConfig`，调用 T2 的 `validate_config`。
- `wiring.py`：`build_engine(config)` 装配默认实现（round_robin / fixed_rounds / CLI 消费）到引擎注册表。

## Definition of Done

- [ ] 测试：YAML 人设名单 + 调度/停止条件解析为 `SessionConfig`；改 YAML 无需改代码（AC-12）
- [ ] 测试：缺 `role_description` 的人设被拒绝加载（AC-13 加载侧）
- [ ] 测试：占位扩展（回显名字角色）经声明式注册可装配（AC-14 定义侧）
- [ ] 测试：`wiring` 装配默认实现到引擎注册表

## Notes

- 与 T3/T4/T5 并行（只依赖 T2）。T11 CLI 的 `--config` / `--personas` 复用本加载器。
- `role_description` 必填（AC-13）在加载时即拒绝，与 T2 的 `validate_config` 同源，不重复实现。
