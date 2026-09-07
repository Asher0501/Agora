# Changelog — agora

## agora — 无语义多方接力协作引擎（library-sdk + CLI）

> **命名**：`agora` 是「多方接力协作引擎」的**引擎层**（把 brainstorm 内核抽成无语义接力层）；`brainstorm` 是它上面的第一个场景（纯 YAML 配置），见 [idea-brief §3](../../idea-brief.md)。

**What:** 把 brainstorm 的「多角色按序接力 + 共享桌面 + 停止条件 + 扩展点」内核抽成**无语义**的接力层 `agora`。场景作者用一份声明式 YAML（`roles`/`select`/`stop`/`summary`）组合出能力集合相同的场景，**零引擎代码改动**。引擎只强制业务无关机制（每 turn 恰好一条发言、条数上限兜底、跨会话/角色命名空间隔离）；配置错误在**加载时**被拒绝并给出可读 `agora.*` 错误码。以 **library-sdk（引擎核心）** + **CLI（`run`/`stop`/`resume`/`observe`）** 两表面交付，默认离线运行（`FakeLLM`，无需 API Key）。

**Why:** brainstorm 已证明该模式可行，但内核被 brainstorm 语义绑死（角色/调度/停止都写成专用 Python 扩展点），换场景要再写一套。agora 把「产出/选人/判停/存储/摘要」降维成**闭集原子菜单** + 声明式配置，让「填一份配置就能跑新场景」成立。详见 [spec §1/§2](spec.md)。关键决策：[ADR-0003](adr/0003-replace-extension-protocols-with-five-atom-menu.md)（五原子闭集菜单取代四扩展协议）、[ADR-0005](adr/0005-validate-config-at-load-time.md)（配置加载时校验为一等能力）、[ADR-0006](adr/0006-resume-from-creation-time-config-snapshot.md)（按创建时快照恢复）、[ADR-0007](adr/0007-check-stop-before-producing-each-turn.md)（判停先于产出）、[ADR-0004](adr/0004-provide-controlled-extension-zone.md)（受控扩展区逃生门）。

**How to use:**

```bash
agora run --config scenarios/brainstorm.yaml --topic "如何让论坛更活跃" --db ./agora.db
agora stop <run_id>      # 手动停止（manual 停止条件；AC-11）
agora resume <run_id>    # 恢复到中断那一轮，已落桌不重放（AC-15）
agora observe <run_id>   # 打印已落盘的观测事件（AC-18）
```

```yaml
scenario: brainstorm
roles:
  - {id: skeptic, prompt: "你是质疑者。主题：{topic}\n已有讨论：{history}", inject: [topic, history], output: free_text}
  - {id: optimizer, prompt: "你是优化者…", inject: [topic, history], output: free_text}
select: {type: round_robin}          # round_robin | llm_pick
stop: {type: fixed_rounds, max: 12}  # fixed_rounds | llm_verdict | manual
# summary: {role: skeptic, key: notes, window: 20}   # 可选：摘要原子 + 跨轮连续性（AC-12）
```

**Operational notes:**
- Migration: 无 —— 复用 weave_agent_sdk 自建 `memory_entries`（`agora:{run_id}:*` 命名空间），无新增 schema。
- Feature flag / config: 全部行为由 YAML 配置驱动；默认离线 `FakeLLM`。
- Rollback: **破坏性重构** —— 旧 brainstorm 四扩展协议被「原子 + 声明式配置」取代，旧会话不保证恢复（spec §3 非目标）；回退 = revert PR（无 DB 迁移需回滚）。

**Acceptance criteria delivered:** AC-01·02·02b·03·04·05·06·07·07b·08·09·10b·11·12·13·14·15·15b·16·17·18（21 项）。其中「并发 relay 同 run 重复产出」竞态窗口在 review r3 决议 **Defer**（单进程单会话模型下不发生），记录于 [spec §8](spec.md)。
