# data-model audit — brainstorm

- **Date:** 2026-08-31
- **Size / route:** M / standard（from `.size` / `.route`）
- **Outcome:** no schema change — logical data model over weave's existing `memory_entries` table; **zero migrations**.

## Staged migrations

**None.** 本特性复用 weave 的 `memory_entries` 表（ADR-0003/0005/0006），不新建表/列/索引。该表由 weave SQLite 后端在首次连接时 `CREATE TABLE IF NOT EXISTS` 自建，无迁移工具、无 `migrations/` 树、无 `.up.sql`/`.down.sql`。

- `docs/features/brainstorm/migrations/` — **不创建**（无迁移可写）。
- **Promote-time convention hint:** N/A —— 无顺序号、无时间戳命名可检测；表由依赖（weave）运行时自建。`implement` 无 `layer: migration` 任务。

## Resolved decisions（本阶段确认，非 ADR）

1. **人设私有记忆 = 会话作用域。** namespace 定为 `persona:{session_id}:{persona_id}:stream|state`（同一人设定义跨会话隔离，符合 spec §8 OQ 默认与 ADR-0005）。已写入 data-model.md。
   - **Note to design:** ADR-0006 的字面 `persona:{id}:stream|state` 记号不精确——`{id}` 未区分「人设定义 id」与「会话内实例 id」。若要让 ADR 与实现一致，可由 `design` / `decide-adr` 回补说明；本阶段不越权改 ADR。
2. **发言排序 = 显式 `seq` 字段。** 引擎给每条发言分配会话内单调递增 `seq`，写入 `content.seq`；`created_at` 仅作并列兜底。这是「0 丢失/重复、追加顺序」不变量的载体（`seq` 无列可索引 → 应用层排序，见下）。

## Convention deviations

**None.** 全程沿用 weave `memory_entries` 的列约定（`namespace`/`access_type`/`key`/`content`/`metadata`/`created_at`/`expires_at`）与 uuid4 `id`。未引入任何 house style、未建任何表/列/索引/CHECK/FK。

## Flagged recommendations（非 ADR，可回改）

- **系统记录（跳过 / 无效选择）落点**：SAD §6 只说「persists 跳过记录 / 无效选择记录」未点名落点。data-model 建议存为独立 namespace `brainstorm:{session_id}:events` 的 `stream` 行（`type: skip|invalid_choice`），保持共享桌面纯净（AC-05 桌面 = 发言）。如需改落点（如并入 state），在 `implement` 前定即可。

## Drift findings

**N/A。** 本特性代码尚未实现（`14_forum` 仅有 docs，`brainstorm/` 包未写），无领域层 struct/field 可作 struct-vs-DDL 映射。唯一现存代码是依赖 `13_weave` 的 SQLite 后端，已直接读源（`weave/memory/backends/sqlite.py`）核对表结构与索引，与 SAD/ADR 一致。

## Breaking-change decompositions

**None**（无既有表改动）。

## `<!-- TBD -->`

**None。** 两处原开放点（私有记忆作用域、发言排序）已在 Socratic 确认中闭合。

## Self-check（4 项必查）

1. **Naming 匹配仓库约定** — 沿用 `memory_entries` 列名与 uuid4 `id`。✓
2. **Down 可逆** — 零迁移，无 CREATE/DROP 需配对；空集满足。✓
3. **FK 索引** — KV 表无 FK（无参照完整性），现有三索引覆盖全部查询；无 FK 列需索引。✓
4. **Convention adherence** — 未强加任何 DB 哲学，全程跟随 weave 约定。✓

**self-check: 4/4 pass。**

## Summary

migrations are staged — **nothing was written into any `migrations/` tree**（本特性本就无迁移；`implement` 亦无 promotion 步骤）。产出仅 `data-model.md`（逻辑模型）。Next stage: `api brainstorm`.
