---
id: T5
title: "实现配置 schema 与加载时校验"
layer: "app"
deps: ["T1", "T2"]
acs: ["AC-03", "AC-04", "AC-13"]
files_hint: ["agora/config/schema.py", "agora/config/validator.py", "agora/config/__init__.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T5 — 实现配置 schema 与加载时校验

## Why

配置加载正确性是 top-1 质量目标（sad §10 QG-1）：非法配置 100% 加载时被拒并给出可读原因（US-07，[ADR-0005](../adr/0005-validate-config-at-load-time.md)）。「已知能力」= 闭集菜单 ∪ 已注册扩展（扩展先注册后加载）。来源：[public-api.md §6](../contracts/public-api.md) + [sad.md §6 Flow 2](../sad.md)。

## What

`agora/config/` 落地三个公开函数（[public-api.md §6](../contracts/public-api.md)）：

- `parse_config(raw) -> ScenarioConfig`：YAML 映射 → 类型，schema 沿用 `atomic-relay.md` §2。
- `validate_config(config, known_capabilities)`：校验不变量，非法即 `raise DomainError`。
- `load_config(path) -> ScenarioConfig`：读 YAML + 解析 + 校验。

**校验面**（每项非法都给出可读 `agora.*` 错误 + 定位到角色/能力）：

- 能力 ∈ 闭集菜单 ∪ 已注册扩展（AC-03 → `agora.unknown_capability`）。
- 角色描述必填（AC-04 → `agora.role_description_required`）。
- `output` 与 `select`/`stop` 匹配（AC-13 → `agora.output_judge_mismatch`，如 free_text 却要 verdict）。
- 模板占位符与 `inject` 字段名匹配；`events` 列为保留 `agent_id`；`max`/`window` 数值合法。

## Definition of Done

- [ ] 校验测试覆盖全部已知非法类别（AC-03/04/13 + 保留字 + 占位符），每类被 `DomainError` 拒绝且 message 可读，全绿。
- [ ] 合法配置（含扩展注册的能力）通过校验、不被误拒。
- [ ] `load_config` 对 `scenarios/brainstorm.yaml`（T12）一旦存在即能通过（后续 T12 验证）。
- [ ] lint + mypy clean。

## Notes

- `known_capabilities` 以 `set[str]` 注入（来自 T6 扩展区 + T2 菜单），校验器不 import extension 模块——与 T6 并行无耦合。
- `SummaryConfig` 最小形状（T1 落位）在此按「有 summary 段则 role/key/window 必填」校验；形状最终以 data-model ratify 为准（api-sync-report §C-2）。
- 运行时值校验（缺主题 AC-02b）**不在这里**——那是 T8 `create_run` 的职责（Flow 3）。
