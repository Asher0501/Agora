---
id: T10
title: "实现 CLI 命令（run/stop/resume/observe）"
layer: "ports"
deps: ["T7", "T8", "T5"]
acs: []
files_hint: ["agora/cli/__init__.py"]
owner: "Asher"
estimate: "M"
status: "todo"
---

# T10 — 实现 CLI 命令（run/stop/resume/observe）

## Why

`cli` 表面（[ADR-0001](../adr/0001-build-agora-as-library-sdk-and-cli.md)）：发起人在本地单进程驱动会话的命令行工具。命令/标志/退出码派生自 [cli.md](../contracts/cli.md)，不手写。

## What

`agora/cli/__init__.py` 用 argparse 落地四个命令（[cli.md](../contracts/cli.md)）：

- `run --config <scenario.yaml> --topic <str> [--stance <str>] [--db <path>]`：加载校验配置（T5）→ 校验运行时值 → `create_run`（T8）→ `relay`（T7）跑到终止 → 打印 `run_id` 与终止产物。
- `stop <run_id>`：`stop_run`，不存在 → 退出码 1（`agora.run_not_found`）。
- `resume <run_id>`：`resume_run`，不存在/损坏 → 退出码 1。
- `observe <run_id>`：订阅并流式打印本 run 进度事件（AC-18），不存在 → 退出码 1。

**退出码**：`0` 成功 / `1` 领域错误（stderr 打印 `错误：<message>（<code>）`）/ `2` 用法错误（argparse）。

## Definition of Done

- [ ] 命令级 e2e 测试全绿：`run` 缺 `--topic` 退出 1、`run` 引用不存在场景退出 1、`stop`/`resume`/`observe` 对不存在 run_id 退出 1、正常路径退出 0 并打印预期产物。
- [ ] UTF-8 输出（Windows 控制台强制 UTF-8，中文不乱码）。
- [ ] lint + mypy clean。

## Notes

- `--db` 默认 `./agora.db`（镜像 brainstorm `cli/__init__.py` 约定，cli.md §1）。
- 零引擎代码：`run` 走纯配置路径；菜单外能力经扩展区注册（T6），CLI 不新增命令（cli.md §4）。
- 无鉴权、无幂等键、无重试/死信（本地单进程，sad §6 flagged items）。
