---
id: T11
title: "装配包导出、DI 与 pyproject"
layer: "wiring"
deps: ["T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"]
acs: []
files_hint: ["agora/__init__.py", "agora/wiring.py", "pyproject.toml"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T11 — 装配包导出、DI 与 pyproject

## Why

把 T1–T10 的模块组装成可导入的 `agora` 包与可运行的 CLI（[ADR-0001](../adr/0001-build-agora-as-library-sdk-and-cli.md) 的 library-sdk + cli 形态；[ADR-0002](../adr/0002-extract-semantics-free-agora-package.md) 的中性包）。公开表面见 [public-api.md §1 模块地图](../contracts/public-api.md)。

## What

- `agora/__init__.py`：公开导出 `types`/`errors`/`namespaces`/`atoms`/`relay`/`session`/`config`/`extension`。
- `agora/wiring.py`：DI 装配——注册五个菜单原子到 registry、构建 Repository + LLM + 扩展 registry，提供 create_run→relay 的一键装配（镜像 brainstorm `wiring.py`）。
- `pyproject.toml`：`[tool.setuptools.packages.find]` 的 `include` 增加 `agora*`；`[project.scripts]` 增加 `agora = "agora.cli:main"`；依赖声明 weave `0.1.0`（SAD §2 正式固定版本）。

## Definition of Done

- [ ] `import agora` 暴露公开表面（类型/原子/relay/session/config/extension/errors/namespaces），冒烟测试可导入。
- [ ] `agora` CLI 入口点经 `pyproject.toml` 注册，`agora --help` 可跑（T10 命令可见）。
- [ ] 依赖方向断言仍成立（领域层零 weave 依赖，`tests/test_domain.py` 不回归）。
- [ ] lint + mypy clean。

## Notes

- `agora/wiring.py` 是**内部**模块（public-api 模块地图不列它），不导出为公开符号。
- 本任务依赖全部 app/infra/ports 任务就绪，是 T13（brainstorm 迁移）与 T15（NFR 测试）的前置。
