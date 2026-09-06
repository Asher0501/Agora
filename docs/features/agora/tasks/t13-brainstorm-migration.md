---
id: T13
title: "迁移 brainstorm 包为场景消费方"
layer: "wiring"
deps: ["T11", "T12"]
acs: []
files_hint: ["brainstorm/", "pyproject.toml"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T13 — 迁移 brainstorm 包为场景消费方

## Why

破坏性重构收尾（[ADR-0002](../adr/0002-extract-semantics-free-agora-package.md)）：brainstorm 的领域类型、命名空间、错误码、引擎、CLI 重写为中性形式后，旧包不再保留引擎代码——`agora` + `scenarios/brainstorm.yaml` 成为唯一路径。旧会话数据不迁移（spec §3）。

## What

- 移除/改造 `brainstorm/`：删除 `engine/`（loop/session/stop/table/registry）、`business/protocols.py`、`weave_adapter/repository.py`、`extensions/` 等引擎代码；`brainstorm/` 残留为「场景消费方」或整体删除。
- 消除中性化前语义：`session.*` 错误码、`brainstorm:`/`persona:` 命名空间、Session/Speech/Persona 类型不再存在于包内。
- `pyproject.toml`：移除或重定向 `brainstorm = "brainstorm.cli:main"` 入口；确认 `agora` 为唯一命令入口。

## Definition of Done

- [ ] `brainstorm/` 不再 import 任何引擎实现；`grep -r "session\.\|brainstorm:\|persona:\|class Session\|class Speech\|class Persona" brainstorm/` 无引擎残留（除迁移说明注释）。
- [ ] `pyproject.toml` 中 brainstorm 脚本入口移除/重定向，`agora` 入口仍在。
- [ ] 包仍可安装、`import agora` 正常（不回归 T11）。
- [ ] lint + mypy clean。

## Notes

- 本任务**不**写新测试逻辑——测试迁移与回归是 T14；本任务只负责代码删除/重定向到「测试可跑」的状态。
- 旧 brainstorm 会话数据不迁移（spec §3 非目标）；破坏性变更被允许。
- 若删除量超预期（如 brainstorm 还有 CLI 使用者），在 T14 前保持「删除到最小可回归」即可，不必追求一次删净。
