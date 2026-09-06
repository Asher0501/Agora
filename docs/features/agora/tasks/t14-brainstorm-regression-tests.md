---
id: T14
title: "迁移 brainstorm 回归测试（58 测试绿）"
layer: "tests"
deps: ["T13"]
acs: ["AC-01"]
files_hint: ["tests/"]
owner: "Asher"
estimate: "L"
status: "todo"
---

# T14 — 迁移 brainstorm 回归测试（58 测试绿）

## Why

AC-01 的实证：「能力集合与头脑风暴相同的场景 = 一份声明式配置，引擎代码零改动」。brainstorm 的 58 个测试迁移到 `agora` + `scenarios/brainstorm.yaml` 全部转绿，证明零代码扩展成立（[ADR-0002](../adr/0002-extract-semantics-free-agora-package.md) 后果）。

## What

将 `tests/` 下 brainstorm 的功能测试迁移到 agora 语义（离线 `FakeLLM`，T4）：

- 会话/接力（`test_loop.py`/`test_lifecycle.py`）、选人/调度（`test_moderator.py`）、判停（`test_stop.py`）、角色/私有状态（`test_persona.py`）、存储（`test_repository.py`）、配置（`test_config.py`）、契约（`test_contract.py`）、域隔离（`test_domain.py`）、集成（`test_integration.py`）、CLI（`test_cli.py`）等迁移到 `agora` 语义与 `brainstorm.yaml` 场景。
- 断言走纯配置路径（load `brainstorm.yaml` → create_run → relay），无任何 brainstorm 引擎 import。

## Definition of Done

- [ ] brainstorm 的全部 58 个测试迁移后**全绿**，且运行的是 `agora` + `scenarios/brainstorm.yaml`（AC-01 实证）。
- [ ] 无残留 brainstorm 引擎 import（`grep -r "from brainstorm" tests/` 为空，或仅存迁移说明）。
- [ ] lint + mypy clean。

## Notes

- 这是本 epic **最大的任务**（L，58 测试迁移），若实现时发现 >1 天，按「会话/接力类」「选人/判停类」「存储/隔离类」拆成 2–3 个子任务，不强行一天塞完。
- 沿用 brainstorm 测试的结构与断言风格，只改 import 与命名（Session→Run 等）。
- NFR 测试（并发/耐久/延迟）不在此任务——那是 T15（brainstorm `test_nfr.py` 单独迁移，含新指标名）。
