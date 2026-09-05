---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0007 — Check stop before producing each turn

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

选人与判停拆成两个原子后（ADR-0003），收敛判断的时序需定：每轮先判停再产出，还是先产出再判停？这是 spec §8 OQ2。

## Decision drivers

- 一致性/耐久（top-3 质量目标）——不额外多产出一条发言。
- AC-09「在下一条发言产出前，已达条数即停」、AC-10b「达上限强制结束，不额外产出」。

## Considered options

1. **拆分 + 判停先于产出** — 每轮：选人 → 判停 →（未停才）产出 → 落桌。
2. **拆分 + 产出后判停** — 被否：裁判宣告收敛时已多落一条发言（收敛前多一条尾巴）。
3. **保留组合主持人原子** — 被否：违背 CONTEXT「选人者/裁判拆分」约定与 atomic-relay §7.3 倾向。

## Decision outcome

**Chosen:** Option 1. 接力循环每轮顺序为：选人 → 判停（fixed_rounds 数条数 / llm_verdict 轮首调 judge / manual 查停止标志）→ 未停才产出并落桌。

## Consequences

**Positive**
- 对齐 AC-09/AC-10b，收敛或达上限时绝不额外多产一条。

**Negative**
- llm_verdict 需在轮首调 judge，judge 的 verdict 输出在产前消费（成本：judge 每轮被调一次，与产出角色调用交织）。

**Neutral**
- 判停原子必须是纯状态函数或轮首可判（fixed_rounds/manual 天然满足，llm_verdict 需在轮首注入历史）。

## Links

- Spec: [[../spec.md]] §8/§5 AC-09/AC-10b
- SAD: [[../sad.md]] §4/§6
- Related ADR: [[0003-replace-extension-protocols-with-five-atom-menu]] · [[0006-resume-from-creation-time-config-snapshot]]
