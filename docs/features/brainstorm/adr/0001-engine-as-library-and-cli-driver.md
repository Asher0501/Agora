---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0001 — Build the brainstorm engine as a library-sdk driven by a CLI

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk）

## Context

本特性把 weave demo 的「多人设各自独立作答、记忆彼此隔离」反转成「多人设围绕主题按序接力发言、所有发言落到共享桌面」的头脑风暴机制。spec §2 目标「引擎与具体框架、具体界面解耦，今天由命令行驱动，未来接前端」，§3 非目标「本迭代不实现 Web 前端」。所以需要决定：这个引擎以及它今天的对外形态，分别是哪些「表面」（surface = 特性拥有的 C4 容器）——它决定 §5 画几个容器、下游 `api` / `sequences` / `tasks` 各产出什么契约形式。

## Decision drivers

- spec §2 Goal：引擎与具体界面解耦，未来接前端不返工。
- spec §3 Non-goal：本迭代无 Web 前端、无观察者角色。
- §1 质量目标：可扩展性（新增一个界面 = 0 内核改动）。
- weave demo 的解耦约定：业务层零框架依赖、适配层唯一接入点。

## Considered options

1. **library-sdk + cli** — 引擎核心作为可复用库（公开 Python API 即契约）+ CLI 驱动器。
2. **backend-service + cli** — 引擎作为后端服务（暴露 HTTP/gRPC/events 接口）+ CLI。
3. **cli（单一表面）** — 引擎只是 CLI 内部实现，不单独成表面。
4. **worker** — 独立后台 worker（额外部署单元）。

## Decision outcome

**Chosen:** library-sdk + cli。引擎核心以库形态交付，公开 Python API（start / run / stop / 注册扩展）即契约，业务层零 weave 依赖；CLI 是今天唯一的对外入口。未来 Web 前端 / 观察者角色作为新的消费界面经扩展点接入，无需改内核——直接满足「引擎与界面解耦」与「可扩展性」两个驱动。

## Consequences

**Positive**
- 引擎与界面解耦：未来前端/观察者经扩展点接入，0 内核改动（spec §6 可扩展性 NFR）。
- 库形态的公开 API 即契约，`api` 阶段产出 `contracts/public-api.md` + `contracts/cli.md`，边界清晰。

**Negative**
- 没有现成的 HTTP 边界：未来接前端时需另加一个服务层（届时补 `backend-service` 表面）。
- 两个表面比单表面多一层任务/测试工作量（`ui` 层除外，本迭代无 UI 表面）。

**Neutral**
- 未来前端成型时可把 `backend-service` 作为新表面补进 `target_surfaces`（增量设计，非推翻本决定）。

## Links

- Spec: [[../spec.md]]
- SAD: [[../sad.md]] §4
