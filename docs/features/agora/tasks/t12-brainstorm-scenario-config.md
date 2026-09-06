---
id: T12
title: "编写 brainstorm.yaml 场景配置"
layer: "docs"
deps: ["T5", "T2"]
acs: []
files_hint: ["scenarios/brainstorm.yaml"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T12 — 编写 brainstorm.yaml 场景配置

## Why

第一个纯配置场景，实证「能力集合相同的场景 = 一份 YAML、零引擎代码」（AC-01 的种子，[ADR-0002](../adr/0002-extract-semantics-free-agora-package.md)/[ADR-0003](../adr/0003-replace-extension-protocols-with-five-atom-menu.md)）。来源：spec §1「配置 = YAML 数据文件」+ `atomic-relay.md` §2 schema + [data-model.md §RUN config 快照](../data-model.md)。

## What

`scenarios/brainstorm.yaml` 用纯 YAML 复现 brainstorm 的能力集合：

- `roles`：brainstorm 的角色集（如主持人/参与者），每个含 `id`/`prompt`/`inject`/`window`/`output`。
- `select`：`round_robin` 或 `llm_pick`（与 brainstorm 调度一致）。
- `stop`：`llm_verdict`（`max` 兜底）或 `fixed_rounds`/`manual`（与 brainstorm 判停一致）。
- 可选 `summary`（若 brainstorm 有跨轮摘要语义）。

## Definition of Done

- [ ] `scenarios/brainstorm.yaml` 通过 `load_config` 校验（T5）——无 `DomainError`。
- [ ] 一个配置加载测试断言该 YAML 合法且 roles/select/stop 解析为预期 `ScenarioConfig`。

## Notes

- 运行时值（`topic`/`stance`）**不写进配置**（spec §1 每场会话注入）。
- 本任务只写配置 + 加载测试；跑通整场会话、证明零代码扩展是 T14 的回归测试职责。
- 配置 schema 沿用 `atomic-relay.md` §2；字段与 data-model §RUN config 快照的 JSON 形状一一对应。
