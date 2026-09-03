# Changelog — brainstorm

## brainstorm — 多角色接力头脑风暴引擎（library-sdk + CLI）

**What:** 新增 `brainstorm` 引擎——给定一个主题与一份人设名单，多个人设围绕主题**按序接力发言**、所有发言落到一张共享、有序、持久化的「桌面」上；由可插拔的**调度策略**决定发言顺序、可插拔的**停止条件**（固定轮数 / 收敛判定 / 手动停止）结束会话。以 **library-sdk（引擎核心）** + **CLI（`create`/`run`/`stop`/`export`）** 两个表面交付，默认离线运行（`FakeLLM`，无需 API Key）。

**Why:** 现有 weave 框架已提供「循环 + 记忆 + 命名空间隔离」，demo 也证明了多人设可并行作答，但缺少一条**共享、按序**的协作循环——这正是头脑风暴需要的。本特性在现成地基上补齐「共享桌面 + 回合调度」，并以四扩展点（角色 / 调度 / 停止 / 消费）保留未来分支的衍生空间。详见 [spec §1/§2](spec.md)。关键决策：[ADR-0002](adr/0002-minimal-kernel-pluggable-extensions.md)（最小内核 + 可插拔扩展）、[ADR-0003](adr/0003-persist-sessions-sqlite-resume.md)（SQLite 持久化 + 按轮恢复）、[ADR-0004](adr/0004-sync-orchestration-events-observability.md)（同步编排 + 事件仅观测）、[ADR-0006](adr/0006-persona-private-memory.md)（人设私有记忆）。

**How to use:**

```bash
brainstorm create --config config.yaml   # 声明式配置；或 --topic/--personas 临时开一场
brainstorm run <session-id>              # 跑到停止条件成立（未跑完自动恢复）
brainstorm stop <session-id>             # 手动停止（manual 停止条件时，best-effort）
brainstorm export <session-id>           # 文本；--format json 输出 Speech[]
```

```yaml
topic: "如何提升留存"
personas:
  - {persona_id: product, name: 产品视角, role_description: "关注用户价值与留存漏斗"}
  - {persona_id: tech,    name: 技术视角, role_description: "关注实现可行性与稳定性"}
scheduler: round_robin          # round_robin | moderator
stop_condition:
  type: fixed_rounds            # fixed_rounds | convergence | manual
  max_speeches: 6
```

改这份 YAML 即可改动话题 / 人设 / 策略 / 停止条件，无需改代码（AC-12）。

**Operational notes:**
- Migration: 无 —— 复用 weave 自建 `memory_entries`，无新增 schema。
- Feature flag / config: 全部行为由 YAML 配置驱动；默认离线 `FakeLLM`。
- Rollback: 纯新增包，无破坏性变更；回退 = revert PR（无 DB 迁移需回滚）。

**Acceptance criteria delivered:** AC-01·02·03·04·04b·05·06·06b·07·07b·08·09·10·10b·11·11b·12·13·14·15。其中 AC-06/06b（跨会话隔离）以「构造隔离」达成、AC-11/11b（手动停止）在 library-sdk 进程内成立（CLI `stop` 为 best-effort）——两者均为评审中的 de-scope 决策，见 [review](_review/review-2026-09-03.md)。
