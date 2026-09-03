---
id: T3
title: "实现记忆仓储：会话状态 + 共享桌面 + 私有记忆 + 系统事件落盘"
layer: "infra"
deps: ["T2"]
acs: ["AC-05", "AC-06", "AC-06b"]
files_hint: ["brainstorm/weave_adapter/repository.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T3 — 实现记忆仓储

## Why

[data-model.md](../data-model.md) 声明「no schema change」——持久化复用 weave 的 `memory_entries` 表，经 `namespace + access_type + key` 区分实体。本任务把逻辑实体映射到这张 KV 表，是 [ADR-0003](../adr/0003-persist-sessions-sqlite-resume.md)「单库 + 会话级 namespace + 可恢复」与 [ADR-0006](../adr/0006-persona-private-memory.md)「私有记忆」的落点。

## What

在 `weave_adapter/repository.py` 提供（经 weave SQLite memory backend 读写 `memory_entries`）：

- 会话状态：`save_session_config` / `update_session_status`（含 `current_seq` 递增）/ `write_conclusion` / `load_session`（恢复用），state key = `config`/`status`/`conclusion`。
- 共享桌面：`append_speech`（seq 严格单调 + `speaker_id`）/ `read_table`（按 seq 升序）。
- 私有记忆：`write_private` / `read_private`（`persona:{sid}:{pid}:stream|state`）。
- 系统事件：`append_event`（`brainstorm:{sid}:events`，`skip`/`invalid_choice`）。

## Definition of Done

- [ ] 集成测试：写入 config/status/conclusion 后可按 key 读回；`append_speech` 后 `read_table` 按 seq 升序完整有序返回（AC-05）
- [ ] 隔离测试：会话 A 的 namespace 写/读不影响会话 B（AC-06 / AC-06b 越界拒绝）
- [ ] 私有记忆测试：persona 仅能读/写自己的 `persona:{sid}:{pid}` namespace，他人不可见
- [ ] 不变量测试：同一会话连续 append 0 丢失 / 0 重复（`seq` 严格单调）

## Notes

- 复用 weave 已建索引 `idx_ns_at`/`idx_ns_key`，**无新增索引**（data-model §Indexes）。`seq` 排序在应用层（JSON content 内无列可索引）。
- `seq` 单调用「当前最大 seq + 1」在应用层保证，而非 DB 自增——直接承载 [QG-1](../sad.md) 追加顺序不变量。
