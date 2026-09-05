---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0005 — Validate config at load time against the closed menu ∪ registered extensions

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

配置成为「准代码」后，非法配置要在加载时被拒（spec §2 目标 3「配置错误加载时发现」）。本轮需定「已知能力」的口径与校验深度。

## Decision drivers

- 配置加载正确性（top-1 质量目标）——非法配置 100% 在加载时被拒。
- spec §6.1 Security——配置注入面，加载校验是第一道闸。
- AC-03/AC-04/AC-13——引用不存在的选人/判停方式、角色缺描述、产出格式与判停不符，都要在加载时拒绝。

## Considered options

1. **校验一等 + 已知 = 菜单 ∪ 已注册扩展** — 扩展先注册、后加载，未注册即拒；非法配置 100% 加载时拒绝 + 可读原因。
2. **仅结构校验** — 被否：AC-03（引用不存在的选人/判停）这类错误退回到运行时，违背 spec §2。

## Decision outcome

**Chosen:** Option 1. 「已知能力」= 闭集菜单 ∪ 已注册扩展能力；校验面覆盖模板占位符、注入字段名、output 与 select/stop 匹配、角色描述必填等；非法配置加载时拒绝并给出哪个角色缺什么/哪个能力不受支持。

## Consequences

**Positive**
- 配置错误在跑之前暴露（US-07），校验是「零代码扩展」的信任前提。

**Negative**
- 校验面广（占位符/注入字段/output 匹配/扩展注册时序都要验），校验器本身需被充分测试。

**Neutral**
- 校验规则随原子菜单同步演进（新原子 = 新校验规则）。

## Links

- Spec: [[../spec.md]] §1/§2/§5
- SAD: [[../sad.md]] §4/§8
- Related ADR: [[0003-replace-extension-protocols-with-five-atom-menu]] · [[0004-provide-controlled-extension-zone]]
