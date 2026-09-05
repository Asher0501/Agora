---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0004 — Provide a controlled extension zone (same-process trusted, unversioned)

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

闭集菜单（ADR-0003）覆盖不了的能力需要一条受控出路（spec §2 目标 5「扩展区不污染标准菜单」）。本轮需定扩展区的形态 + 两个开放问题：OQ5（是否承诺稳定/版本化）、OQ7（信任边界）。

## Decision drivers

- spec §2 目标 5——菜单之外的能力有出路，但不污染标准菜单。
- spec §6.1 Security——扩展区代码的信任边界。
- spec §8 OQ5 默认（不承诺版本化）、OQ7 默认（同进程受信）。

## Considered options

1. **受控扩展区 + 同进程受信** — 独立于标准菜单、接口风格可自定义、不承诺稳定/版本化、同进程受信、读范围以 AC-16/17 为界。
2. **扩展区沙箱化（独立进程）** — 被否：IPC 协议/序列化/超时大幅增复杂度，与「内部门逃生门」定位不符，拖慢迁移实证。
3. **本轮不做扩展区** — 被否：违背 spec §2 目标 5，AC-14 无法验收。

## Decision outcome

**Chosen:** Option 1. 受控扩展区；OQ5 = 不承诺稳定/版本化（本轮）；OQ7 = 同进程、视为受信代码、读范围以 AC-16/17 为界（不跨命名空间）。

## Consequences

**Positive**
- 标准菜单保持「零代码 + 严格校验」，不被自定义能力污染。

**Negative**
- 扩展区代码在进程内能触及其它会话数据（无沙箱隔离），信任建立在「扩展者可信」上。

**Neutral**
- 本轮不承诺 ABI 稳定；未来需要时再版本化。

## Links

- Spec: [[../spec.md]] §2/§6.1/§8
- SAD: [[../sad.md]] §4/§8
- Related ADR: [[0003-replace-extension-protocols-with-five-atom-menu]]
