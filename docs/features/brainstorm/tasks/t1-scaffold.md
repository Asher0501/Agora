---
id: T1
title: "搭建 brainstorm 包骨架与测试骨架"
layer: "wiring"
deps: []
acs: []
files_hint: ["pyproject.toml", "brainstorm/", "tests/"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T1 — 搭建 brainstorm 包骨架与测试骨架

## Why

本特性在 `14_forum`（全新工程，无 `architecture-map.md`）落地一个 Python 库。先有可安装、可测试的包骨架，后续 T2–T12 才有落点。结构沿用 [sad §5 分层](../sad.md)（`business/` `engine/` `extensions/` `weave_adapter/` `cli/`）与 [sad §2 约束](../sad.md)（Python 3.11+、weave 0.1.0 外部依赖）。

## What

- `pyproject.toml`：包名 `brainstorm`，`requires-python = ">=3.11"`，依赖 `weave 0.1.0`（`pip install -e .`）+ `PyYAML`；声明 pytest 配置。
- `brainstorm/` 下五个子包的空骨架（`__init__.py`）：`business/` `engine/` `extensions/` `weave_adapter/` `cli/`。
- `tests/` 目录 + 一个冒烟测试：导入五个子包成功。

## Definition of Done

- [ ] `pip install -e .` 成功，`import brainstorm` 可用
- [ ] `pytest` 可运行（空测试集为绿）
- [ ] 冒烟测试：导入 `business`/`engine`/`extensions`/`weave_adapter`/`cli` 五个子包成功

## Notes

- 后续任务 `files_hint` 均落在这五个子包内；本任务只建骨架，不写业务逻辑。
- 分支在 `feature/brainstorm` 上开发；提交用 `SDD-Task: T1` trailer。
