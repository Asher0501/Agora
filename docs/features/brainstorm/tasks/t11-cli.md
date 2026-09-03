---
id: T11
title: "实现 CLI 命令 create / run / stop / export 与退出码"
layer: "ports"
deps: ["T7", "T6", "T8", "T9", "T10"]
acs: []
files_hint: ["brainstorm/cli/"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T11 — 实现 CLI 命令 create / run / stop / export

## Why

CLI 是 library-sdk 今天唯一的对外入口（[ADR-0001](../adr/0001-engine-as-library-and-cli-driver.md)），命令与引擎操作一一对应。派生自 [contracts/cli.md](../contracts/cli.md) 与 [sad §5 C4 Container](../sad.md)「Brainstorm CLI」。

## What

- `cli/` 入口 `brainstorm`：`create` / `run` / `stop` / `export` 四命令，映射到 T7/T8/T9/T10 的引擎操作。
- flags（`--topic`/`--personas`/`--scheduler`/`--stop-condition`/`--max-speeches`/`--config`，`export --format`）。
- 退出码映射：0 成功 / 2 用法错误 / 1 领域拒绝（带 `code`），见 `cli.md` Exit codes。
- `--config` 与单项 flag 二选一（复用 T6 加载器）。

## Definition of Done

- [ ] e2e：`brainstorm create --topic ... --personas ...` 输出 `session_id`；`run`/`stop`/`export` 按 [contracts/cli.md](../contracts/cli.md) 输出
- [ ] 测试：领域拒绝映射到退出码 1 并带 `code`，用法错误退出码 2
- [ ] 测试：`--config` 与单项 flag 互斥；`export --format json` 输出 `Speech[]`

## Notes

- CLI 是 `Consumer` 扩展点的默认实现（订阅进度事件打印）；stdout 结果 / stderr 错误，见 `cli.md` I/O 约定。
- 依赖 T7/T8/T9/T10 全量引擎操作就绪；本任务不实现任何引擎逻辑。
