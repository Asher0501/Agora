---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0001 — Build agora as a library-sdk driven by a CLI

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

agora 是「多方接力协作引擎」的引擎层泛化：目标用户是**场景作者**（写配置）与**发起人**（跑会话），无人类 UI 表面（spec §3 非目标「不做 Web 前端/论坛界面」）。需要决定「引擎以什么形态交付」。

## Decision drivers

- spec §2「引擎与场景语义解耦」——交付形态要能承载「库接口即契约」。
- 零代码扩展（spec §7 KPI）——内核作为库暴露公开 Python API，场景作者经它组合原子。
- brainstorm 先例（ADR-0001 同形）——已被证明可行的形态，避免引入额外技术变量。

## Considered options

1. **library-sdk + cli** — 引擎作为库发布（公开签名/类型即契约），CLI 作为驱动器。
2. **backend-service** — 常驻 HTTP/gRPC 服务。被否：spec 未要求远程/多租户形态，引入网络拓扑/鉴权/多副本复杂度。
3. **worker** — 常驻后台消费者。被否：agora 是同步进程内编排，事件仅作观测（沿用 brainstorm ADR-0004）。

## Decision outcome

**Chosen:** Option 1. library-sdk（引擎内核）+ cli（命令行驱动器），与 brainstorm 同形，零 UI 表面。

## Consequences

**Positive**
- 匹配 brainstorm 基线，迁移实证不被额外技术变量干扰。
- 库接口即契约，`api` 阶段导出 `contracts/public-api.md` 与 `contracts/cli.md`。

**Negative**
- 无 HTTP 表面——未来「论坛界面」（roadmap 步骤 5）需在 library-sdk 之上再包 backend-service。

**Neutral**
- 未来加 backend-service 是「在库之上加一层」，不推翻本决策。

## Links

- Spec: [[../spec.md]] §1/§4
- SAD: [[../sad.md]] §4
- Related ADR: [[0003-replace-extension-protocols-with-five-atom-menu]]
