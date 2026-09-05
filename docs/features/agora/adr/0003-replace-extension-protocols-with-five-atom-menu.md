---
status: Accepted
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-05"
feature_size: "L"
ticket: ""
---

# 0003 — Replace the four extension protocols with a five-atom closed menu + declarative config

- **Status:** Accepted
- **Date:** 2026-09-05
- **Deciders:** Asher（Architect）

## Context

brainstorm 的四扩展协议（Role / Scheduler / StopCondition / Consumer，`business/protocols.py`）把「会重复出现的能力」写成 Python 协议 + 各自实现，换一个场景就得再写一套。agora 要把它降维成「配置 + 少量原子」。

## Decision drivers

- 零代码扩展（spec §2/§7）——能力集合相同的场景 = 一份 YAML 配置，零引擎代码。
- 配置加载正确性（top-1 质量目标）——原子菜单是「已知能力」闭集的锚点。
- US-06「角色维持跨轮连续性」——摘要需作为一等原子支撑。

## Considered options

1. **五原子菜单 + YAML 配置** — 产出 / 选人 / 判停 / 存储 / 摘要五个原子，场景 = YAML（roles/select/stop）+ 运行时值注入。
2. **四原子（摘要并入产出）** — 被否：US-06 的跨轮连续性沦为产出注入的隐式行为，摘要失去一等的存储/触发语义。

## Decision outcome

**Chosen:** Option 1. 闭集菜单 = 产出（模板+注入+LLM+解析）、选人（round_robin/llm_pick）、判停（fixed_rounds/llm_verdict/manual）、存储（StreamStore+StateStore namespace KV）、摘要（共享转录压缩进角色私有状态）。配置 schema 沿用 `atomic-relay.md` §2。

## Consequences

**Positive**
- 新场景零代码；菜单语义明确，「已知能力」校验有锚点。

**Negative**
- 菜单之外的能力必须走扩展区（见 ADR-0004）。

**Neutral**
- 原子清单是固定但可扩展的——「新能力 = 新原子 = 写代码」。

## Links

- Spec: [[../spec.md]] §1/§2
- SAD: [[../sad.md]] §4
- Related ADR: [[0004-provide-controlled-extension-zone]] · [[0005-validate-config-at-load-time]]
