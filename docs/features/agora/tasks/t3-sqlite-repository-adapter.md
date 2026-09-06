---
id: T3
title: "实现 SQLite Repository 适配（weave memory_entries）"
layer: "infra"
deps: ["T1", "T2"]
acs: ["AC-16", "AC-17"]
files_hint: ["agora/adapter/repository.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T3 — 实现 SQLite Repository 适配（weave memory_entries）

## Why

唯一 weave 集成点（SAD §5 `adapter/repository.py`，SAD §2 单向依赖）。持久化复用 weave 的 `memory_entries` 单表，无 schema change（[data-model.md](../data-model.md)「No schema change」），只做**逻辑模型 → 单张 KV 表**的映射。跨会话/角色隔离（AC-16/17）由 namespace 构造保证——越界查询在存储层即不可见。

## What

`agora/adapter/repository.py` 实现 `Repository`，满足 T2 的 `StreamStore`/`StateStore` 协议，经 weave `memory_entries`（`namespace` + `access_type` + `key`）：

- **转录追加**：`stream_append` 写 `agora:{run_id}:stream`，content 为 `{seq, agent_id, text}`（data-model §TURN）。
- **读完整转录**：`WHERE namespace='agora:{run_id}:stream' AND access_type='stream'` 取回后按 `seq` 升序（应用层排序，data-model §Indexes）。
- **状态读写**：`agora:{run_id}:state` 按 key 分 `config`/`status`/`verdict`/`recap`（data-model §RUN State key）。
- **私有状态**：`agora:{run_id}:{agent_id}:state`（keyed）与 `:stream`（append-only 便签）；读路径只带本 agent 的 namespace（AC-16/17 结构性隔离）。
- **观测事件**：`agora:{run_id}:events:stream`（`invalid_choice`/`verdict_parse_failure`，非转录，data-model §System records）。

## Definition of Done

- [ ] 隔离断言单测全绿（AC-16/17）：以会话 A 角色/发起人构造的查询，对会话 B 的 namespace 返回空、不暴露他角色私有状态。
- [ ] 追加 + 按 seq 有序读单测全绿（支撑 T7 的追加顺序不变量）。
- [ ] config 快照写一次后可读、不覆盖（ADR-0006 不可变快照）；status/verdict/recap 按 key 读写正确。
- [ ] 复用 weave 已有索引（`idx_ns_at`/`idx_ns_key`），无新增索引（data-model §Indexes）。
- [ ] lint + mypy clean。

## Notes

- 本任务是唯一 `import weave` 的存储集成点；领域层（T1/T2）不得 import 它。
- `seq` 在 JSON content 里、无列可索引——按 `created_at` 取回后应用层 `ORDER BY seq`（data-model 明示）。
- 与 T7（接力循环读/写转录）、T8（会话状态/快照）共享同一文件契约，但不改其文件。
