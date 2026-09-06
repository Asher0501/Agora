---
id: T1
title: "建立中性领域类型、错误码与命名空间"
layer: "domain"
deps: []
acs: []
files_hint: ["agora/types.py", "agora/errors.py", "agora/namespaces.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T1 — 建立中性领域类型、错误码与命名空间

## Why

新建 `agora/` 中性包的领域基石（[ADR-0002](../adr/0002-extract-semantics-free-agora-package.md)）：把 brainstorm 的 Session/Speech/Persona 中性化为 Run/Turn/Agent、`brainstorm:`/`persona:` 根中性化为 `agora:*`、`session.*` 错误码中性化为 `agora.*`。类型/命名空间/错误码是后续原子（T2）、存储（T3）、校验（T5）、接力（T7）、会话（T8）共用的契约，来源是 [public-api.md](../contracts/public-api.md) §2/§3/§7 与 [data-model.md](../data-model.md) §Entities/§Namespace scheme。

## What

落地三个纯模块（零 weave 依赖，SAD §2 单向依赖）：

- `agora/types.py` — [public-api.md §2](../contracts/public-api.md) 的 frozen dataclass：`RoleConfig`/`SelectConfig`/`StopConfig`/`SummaryConfig`/`ScenarioConfig`/`RuntimeValues`/`Run`/`Turn`/`Agent`/`Verdict`/`Recap`/`RunOutcome` + `Literal` 枚举（`RunStatus`/`SelectKind`/`StopKind`/`OutputKind`/`Termination`）。`SummaryConfig` 形状在 api-sync-report §C-2 未定义——本任务先按**最小形状**（`role`/`key`/`window`）落位并注释「待 data-model ratify」。
- `agora/errors.py` — [public-api.md §3](../contracts/public-api.md) 的 `DomainError(code, message, details?)` + 9 个错误码登记（`agora.unknown_capability`/`role_description_required`/`output_judge_mismatch`/`scenario_not_found`/`runtime_value_required`/`run_not_found`/`run_corrupted`/`invalid_state`/`turn_already_produced`）。
- `agora/namespaces.py` — [public-api.md §7](../contracts/public-api.md) 的 5 个构造器：`run_stream_ns`/`run_state_ns`/`run_events_ns`/`agent_stream_ns`/`agent_state_ns`，精确产出 `agora:{run_id}:*` 形式（`events` 是保留段，`agent_id` 不得为 `"events"`）。

## Definition of Done

- [ ] `tests/test_domain.py` 全绿：断言 `agora/types.py`/`errors.py`/`namespaces.py` **零 import weave**（镜像现有 business 层隔离断言）。
- [ ] 命名空间构造器输出精确匹配 data-model §Namespace scheme 的 5 种串。
- [ ] `DomainError.to_dict()` 产出 `{code, message[, details]}`，9 个错误码一一登记（对应 AC-02b/03/04/13/15b，见 T5/T8）。
- [ ] lint + mypy clean（`pyproject.toml` 的 ruff/mypy 规则）。

## Notes

- 命名用 **`run_id`** 而非 `session_id`（data-model + public-api 已中性化；`sad.md` §2/§6/§8 的 `session_id` 残留是 design 的 owner，见 _epic §Risks）。
- 类型是后续所有任务的编译契约，但 Python 非「静态强制」语言，无 compile-coupled 拆分之需——本任务独立可绿。
