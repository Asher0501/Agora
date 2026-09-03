---
id: T13
title: "编写 README：用法、配置示例与扩展点说明"
layer: "docs"
deps: ["T11"]
acs: []
files_hint: ["brainstorm/README.md"]
owner: "Asher"
estimate: "S"
status: "todo"
---

# T13 — 编写 README

## Why

brainstorm 是 library-sdk（[ADR-0001](../adr/0001-engine-as-library-and-cli-driver.md)），公开 Python API 即契约。README 是未来消费者（含衍生分支：Web 论坛、观察者角色）的第一入口，记录用法 + 配置 + 扩展点，**链接**上游、不重复正文。

## What

- `brainstorm/README.md`：安装、CLI 四命令用法、YAML 配置示例、四扩展点接入示例（Role/Scheduler/StopCondition/Consumer）。
- 链接到 [spec](../spec.md) / [sad](../sad.md) / [data-model](../data-model.md) / [public-api](../contracts/public-api.md) / [cli](../contracts/cli.md)。

## Definition of Done

- [ ] README 覆盖 create/run/stop/export 用法 + YAML 配置示例 + 四扩展点接入说明
- [ ] 链接 spec/sad/data-model/contracts，不重复正文

## Notes

- 依赖 T11（命令与退出码已定型），否则 README 的用法会与实际不符。
- 未来分支（观察者角色 / 论坛界面）经扩展点接入，README 的扩展点章节是它们的落点（spec §2 可扩展性）。
