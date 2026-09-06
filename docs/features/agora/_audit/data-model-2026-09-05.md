# data-model audit — agora

- **Date:** 2026-09-05
- **Size / route:** L / full（from `.size` / `.route`）
- **Outcome:** no schema change — 复用 weave 现有 `memory_entries` 表的逻辑数据模型 + 命名空间中性化（`brainstorm:`/`persona:` → `agora:*`，Session/Speech/Persona → Run/Turn/Agent）；**zero migrations**.

## Staged migrations

**None.** 本特性复用 weave 的 `memory_entries` 表（SAD §2/§4 + ADR-0006），不新建表/列/索引。该表由 weave SQLite 后端在首次连接时 `CREATE TABLE IF NOT EXISTS` 自建，无迁移工具、无 `migrations/` 树、无 `.up.sql`/`.down.sql`。

- `docs/features/agora/migrations/` — **不创建**（无迁移可写）。
- **Promote-time convention hint:** N/A —— 无顺序号、无时间戳命名可检测；表由依赖（weave）运行时自建。`implement` 无 `layer: migration` 任务。

## Resolved decisions（本阶段确认，2 项经用户确认，其余推断自 SAD/ADR）

1. **命名空间完全中性化（用户确认）。** 单根 `agora:{run_id}:*`，共享转录 `agora:{run_id}:stream`、run 状态 `agora:{run_id}:state`、系统事件 `agora:{run_id}:events:stream`、agent 私有 `agora:{run_id}:{agent_id}:stream|state`。领域类型 Run/Turn/Agent/Transcript 取代 Session/Speech/Persona（SAD §2/§5）。
   - **Note to design:** SAD §8 交叉关注与 §12 术语表仍写字面 `session_id`（「ID strategy | `session_id`（UUID）」「中性命名空间 | `agora:{session_id}:*`」），与本模型锁定的 `run_id` 冲突。请 `design` 回改这两处的措辞为 `run_id`（本阶段不越权改 SAD，仅标出）。
2. **配置快照折叠运行时值（用户确认）。** 单个 state key `config` = `{"scenario": <场景配置>, "runtime": <运行时值>}`，创建时写一次、不可变（ADR-0006「定格」）。resume 读快照、不重读磁盘配置。
3. **termination 产物拆两个 state key。** `verdict`（裁判收敛判断，仅 `llm_verdict` 且宣告收敛路径写）+ `recap`（全局复盘，任意终止路径都写，`termination` 标注 converged / fixed_rounds / cap_unconverged / manual）。brainstorm 的单一 `conclusion` key 拆成两个，因 CONTEXT 术语表明确区分「结论（Verdict）≠ 总结（Final recap）」。
4. **turn 排序 = 显式 `seq` 字段。** 引擎给每条发言分配 run 内单调递增 `seq`，写入 `content.seq`；`created_at` 仅作并列兜底（沿用 brainstorm 已确认的「0 丢失/重复」不变量载体）。
5. **观测事件落点 = 独立 namespace `agora:{run_id}:events:stream`。** 与 AC-18 的进程内「进度事件」（不持久化）区分：本节是「记录」性质，落盘但不在转录读取路径上。

## Convention deviations

**None（有意收敛除外）。** 全程沿用 weave `memory_entries` 的列约定与 uuid4 `id`，未引入任何 house style、未建任何表/列/索引/CHECK/FK。命名空间根从 `brainstorm:`/`persona:` 变为 `agora:*` 是**有意中性化**（ADR-0002 + 用户确认），非无意的风格偏离。

## Flagged recommendations（非 ADR，可回改）

- **保留段 `events`：** agent 私有 namespace 与系统事件共享单根 `agora:{run_id}:*`，`agent_id` 若取 `"events"` 会与系统事件 namespace `agora:{run_id}:events:stream` 撞名。建议 `config/validator.py` 把 `events` 列为 `roles[].id` 的保留字（ADR-0005 校验面的一小项）。brainstorm 因私有走 `persona:` 根而天然不撞，agora 收敛单根后此风险首次出现。
- **AGENT 完整配置字段归 `config/schema.py`：** 本模型只锁定 AGENT 身份 `(run_id, agent_id)` 与私有状态归属；`roles[].prompt/inject/window/output` 的精确 schema 由 `config/schema.py`（SAD §5）+ `atomic-relay.md` §2 / ADR-0003 定义，data-model 不重复推导。`atomic-relay.md` §2 未列 `role_description` 独立字段、但 prompt 模板占位符含 `{role_description}`——该字段的来源与注入在 `api`/`tasks` 阶段定。

## Drift findings

**N/A（结构上）。** agora 是新包、尚未实现，无领域层 struct/field 可作 struct-vs-DDL 映射。现存代码是**被重构的对象**——brainstorm 的 `business/namespaces.py`（`brainstorm:`/`persona:` 根）、`business/types.py`（Session/Speech/Persona）、`weave_adapter/repository.py`（三 state key config/status/conclusion）——已直接读源核对：agora 的中性化模型正是对这些的破坏性替换（ADR-0002，旧数据不迁移，spec §3）。无列级 drift。

## Breaking-change decompositions

**None**（无既有表改动；旧 brainstorm 会话数据本就不迁移，spec §3）。

## `<!-- TBD -->`

**None。** 两处原开放点（命名空间中性化深度、运行时值落点）已在本轮用户确认中闭合；verdict/recap 拆分与 `seq` 排序继承 brainstorm 已确认结论。

## Self-check（4 项必查）

1. **Naming 匹配仓库约定** — 沿用 `memory_entries` 列名与 uuid4 `id`；命名空间中性化为 `agora:*` 是 SAD §2/§5 + ADR-0002 的明确要求（用户确认）。✓
2. **Down 可逆** — 零迁移，无 CREATE/DROP 需配对；空集满足。✓
3. **FK 索引** — KV 表无 FK（无参照完整性），weave 现有三索引覆盖全部查询（转录读 / state 读 / TTL）；无 FK 列需额外索引。✓
4. **Convention adherence** — 未强加任何 DB 哲学，全程跟随 weave 约定；唯一「偏离」是 SAD 明文要求的中性化，已记录。✓

**self-check: 4/4 pass。**

## Summary

migrations are staged — **nothing was written into any `migrations/` tree**（本特性本就无迁移；`implement` 亦无 promotion 步骤）。产出仅 `data-model.md`（逻辑模型 + 中性命名空间方案）。ER 图经结构 lint 校验（无 `mmdc`/`node_modules/mermaid` 可用，走 mermaid-check 的第 4 级 fallback：首 token `erDiagram`、四实体均声明、边只引用已声明实体、cardinality `||--o{` 合法、属性行 `type name` 格式、无占位符、括号/引号平衡）。Next stage: `api agora`.
