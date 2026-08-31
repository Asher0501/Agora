---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
ticket: ""
---

# 0002 — Keep the engine kernel minimal (orchestration loop only)

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Asher + Architect（Socratic walk）

## Context

spec §1 承诺「稳定内核 + 可插拔扩展点」，§6 可扩展性 NFR 是「新增一个角色/策略/界面 = 0 内核改动」。需要决定：引擎内核里写死哪些东西、哪些是可替换的扩展点。spec §8 OQ 给出默认「最小内核（仅会话编排循环）」。

## Decision drivers

- spec §6 NFR：新增角色/策略/界面 = 0 内核改动。
- spec §8 OQ 默认：最小内核（仅会话编排循环）。
- §1 质量目标：可扩展性。

## Considered options

1. **最小内核** — 内核只含会话生命周期、回合循环、共享桌面、扩展注册；调度/停止/角色/界面都是扩展。
2. **内核内置默认策略** — round-robin + 固定轮数停写进内核，扩展点只覆盖变体。

## Decision outcome

**Chosen:** 最小内核。内核四样：会话生命周期、回合编排循环、共享桌面（append-only、标记发言者）、扩展注册表。round-robin 调度、固定轮数停止、路由者、CLI 都是「默认扩展实现」，装配时注册；内核只认识「调度器」「停止条件」接口，不知道具体策略。共享桌面是「0 丢失/重复」不变量的唯一载体，故为内核不可插拔部分。

## Consequences

**Positive**
- 兑现可扩展性 NFR：新角色/调度策略/停止条件/界面经扩展点接入，0 内核改动。
- 未来分支（观察者角色、Web 论坛界面）不触碰内核，回归风险低。

**Negative**
- 多一层抽象（接口 + 注册 + 默认实现），比「写死默认策略」多一点样板。
- 内核/扩展的边界文档必须清晰，否则未来开发者会误把扩展实现塞回内核。

**Neutral**
- 扩展点数量（4 个：角色 / 调度策略 / 停止条件 / 消费界面）是设计约定，未来新增扩展点需经 blast-radius 门再判。

## Links

- Spec: [[../spec.md]]
- SAD: [[../sad.md]] §4
