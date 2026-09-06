---
id: T8
title: "实现会话生命周期（create/resume/stop/read）"
layer: "app"
deps: ["T1", "T3", "T5"]
acs: ["AC-02", "AC-02b", "AC-11", "AC-15", "AC-15b"]
files_hint: ["agora/session.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T8 — 实现会话生命周期（create/resume/stop/read）

## Why

会话生命周期公开入口（[public-api.md §5](../contracts/public-api.md)）：创建（AC-02/02b）、恢复（AC-15/15b，[ADR-0006](../adr/0006-resume-from-creation-time-config-snapshot.md)）、手动停止（AC-11）、读转录。来源：[sad.md §6 Flow 3/8/10/12](../sad.md)。

## What

`agora/session.py` 落地：

- `create_run(repository, scenario, runtime) -> Run`：校验场景存在（`agora.scenario_not_found`）、运行时值必填如缺主题（`agora.runtime_value_required`，AC-02b）→ 校验配置（T5 `validate_config`）→ 写 config 快照（scenario+runtime 折叠为不可变快照，ADR-0006）→ 建 `running` Run（AC-02）。
- `resume_run(repository, run_id) -> Run`：读快照 + 已落桌转录 + 各角色私有状态重建；不存在 → `agora.run_not_found`、损坏 → `agora.run_corrupted`（AC-15b）；已落桌不重放、在途丢弃该轮重试（AC-15）。
- `stop_run(repository, registry, run_id) -> RunOutcome`：取消在途生成（该发言不落桌）、写停止标志 + `recap` 标注「手动停止」（AC-11）。
- `read_transcript(repository, run_id) -> list[Turn]`：按 seq 升序（AC-16/17 隔离内的本 run 读路径）。
- `subscribe(registry, observer)`：订阅进度事件（AC-18 入口，进程内）。

## Definition of Done

- [ ] create_run 单测：合法启动建 Run 并写快照（AC-02）；缺主题/引用不存在场景被拒（AC-02b）。
- [ ] resume_run 单测：恢复已落桌不重放不丢失、私有状态一并恢复（AC-15）；不存在/损坏被拒（AC-15b）。
- [ ] stop_run 单测：取消在途 + 写「手动停止」recap（AC-11）。
- [ ] read_transcript 按 seq 有序单测。
- [ ] lint + mypy clean。

## Notes

- `stop_run` 与 T7 `manual` 判停经 run state 的停止标志协作（本任务写、T7 读），不 import `relay`。
- 运行时值校验（AC-02b）在本任务，配置结构校验（AC-03/04/13）在 T5——`create_run` 调用 T5 的 `validate_config`。
- resume 读**快照**、不重读磁盘配置（ADR-0006）；改配置只影响新会话。
