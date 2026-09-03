---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-08-31"
feature_size: "M"
---

# Test plan — brainstorm

> 本特性交付一个「多个人设围绕主题、按序接力发言、所有发言共享可见」的头脑风暴引擎：内核（library-sdk）+ CLI 驱动器，会话按停止条件结束，角色/调度/停止/消费界面为可插拔扩展点。下表把 spec.md §5 的每一条验收标准（AC）映射到至少一条测试，并固定层级与数据策略。本计划在任何测试存在**之前**写下，`implement` 照此写红测试。

## Levels

本特性无 UI 表面（`sad.md` frontmatter `target_surfaces: [library-sdk, cli]`），故 UI 三层（Component / Visual-regression / E2E-through-UI）不适用。适用层级如下；`implement` 按仓库现有约定挑具体工具，此处只点名层级、不写工具名。

| Level | Scope | Strategy (generic — no tool names) |
|---|---|---|
| Unit | 纯逻辑：一条规则、一次校验、一个计算——无 I/O。 | 进程内、无外部依赖。 |
| Integration | 模块对其拥有的真实依赖（存储 / 缓存 / 队列）。 | 一个临时真实依赖（throwaway SQLite），套件级拉起、用后拆除。 |
| Contract | 两个参与者之间的边界——双方约定的 API 形态或事件 schema。 | 用真实形态对文档契约核对；不手写桩。 |
| E2E | 一条完整端到端流程（每条关键 user story 一条）。 | 经真实入口（CLI 命令）驱动，配临时依赖。 |
| Load | NFR 校验——仅当 NFR 带数字。 | 仓库已有负载工具，或 e.g. k6 / Locust。 |
| Component *(UI 表面才用)* | <!-- N/A: no UI surface --> | — |
| Visual-regression *(web UI 才用)* | <!-- N/A: no UI surface --> | — |
| E2E-through-UI *(UI 表面才用)* | <!-- N/A: no UI surface --> | — |

## AC coverage

spec.md §5 共 20 条 AC，逐条映射如下。**零未覆盖**。期望结果用大白话写，不含状态码 / 错误码字符串 / SQL。

| AC (spec.md §5) | Test name (intent-based) | Level | Expected outcome |
|---|---|---|---|
| AC-01 <happy path> | session start persists topic and roster | integration + e2e | 会话被创建并落盘主题与人设名单，返回「已开始」的确认 |
| AC-02 <error> | empty topic is rejected | unit | 启动被阻止，提示主题不能为空，且不产生任何会话写入 |
| AC-03 <domain invariant> | fewer than two unique personas is rejected | unit | 启动被阻止，明确提示「至少需要两位参与者」 |
| AC-04 <happy path> | a turn produces and records the next in-order speech | integration + e2e | 该参与者产出一条承接主题与历史发言的发言，按序落桌并标注发言者 |
| AC-04b <error> | failed generation retries then skips and records the skip | integration | 重试若干次仍失败则跳过该参与者并记录原因，会话继续推进 |
| AC-05 <happy path> | table read returns complete ordered speaker-annotated speeches | integration + e2e | 返回完整、按序、标注发言者的全部发言列表 |
| AC-06 <authorization> | cross-session append is unreachable (namespace isolation) | integration | 越界写入不可达（构造隔离），目标会话桌面保持不变 |
| AC-06b <authorization> | cross-session read is unreachable (namespace isolation) | integration | 越界读取不可达（构造隔离），目标会话桌面内容不向该参与者暴露 |
| AC-07 <happy path> | moderator freely picks the next speaker or announces convergence | integration + e2e | 路由者自由选定下一位发言者或宣布收敛；选人约束只由人设描述表达，不硬编码在引擎内 |
| AC-07b <error> | invalid moderator choice falls back to round-robin and is recorded | integration | 回退到固定轮转选取下一位，并记录这次无效选择 |
| AC-08 <cross-context> | moderator decides continue or end from context; end yields a conclusion | integration + e2e | 路由者结合桌面状态与停止条件裁决继续或结束，结束时给出结论 |
| AC-09 <happy path> | fixed rounds auto-ends and produces the full record | integration + e2e | 跑完配置轮数后自动结束，产出完整讨论记录 |
| AC-10 <happy path> | convergence ends the session with a conclusion | integration + e2e | 宣布收敛后结束会话，并附带一份结论或摘要 |
| AC-10b <domain invariant> | convergence that never converges force-ends at the cap marked not-converged | integration | 达到最大轮数上限仍不收敛时强制结束，并标注「未收敛」 |
| AC-11 <happy path> | manual stop ends the session and retains the record | integration | 停止指令立即结束会话并保留当前讨论记录（library-sdk 进程内） |
| AC-11b <domain invariant> | stop during an in-flight speech waits for it to land | integration | 等待在途发言落桌后再结束，保证该发言不丢失 |
| AC-12 <happy path> | changed config runs as-is with no code change | integration | 新配置直接生效，无需改动任何代码 |
| AC-13 <domain invariant> | persona missing a role description is rejected at load | unit | 拒绝加载，指明该人设必须提供角色描述 |
| AC-14 <happy path> | placeholder extension runs through the extension point with the kernel unchanged | contract + integration | 占位扩展在会话中生效，内核循环未改动 |
| AC-15 <domain invariant> | second append in one round is blocked | integration | 阻止本轮二次追加，说明该参与者本轮的发言名额已用 |

**e2e 流程（CLI 层，`brainstorm create → run → export`）与 AC 的对应**：上表标 `+ e2e` 的 AC 由以下两条端到端流程覆盖——① 固定轮数全程（覆盖 AC-01/04/05/09）、② 路由者收敛全程（AC-07/08/10）。手动停止（AC-11/11b）为 library-sdk 进程内语义（CLI `stop` 是独立进程、best-effort，见 spec §3），只在集成层测。AC-04b / AC-06 / AC-06b / AC-07b / AC-10b / AC-11b / AC-15 的失败与授权分支在 CLI 层难以稳定触发，只在集成层测（各有专属测试行，见下节）。

**横跨多个 AC 的 contract 测试**（不计入上表单条 AC 归属，但被 `implement` 读取）：

- `public-api surface and error sentinels match the contract` — 断言引擎公开操作（`create_session` / `run_session` / `stop_session` / `resume_session` / `read_table` / 扩展注册）与 error 哨兵码集合与 `contracts/public-api.md` §3/§5 一致。这从契约侧覆盖 AC-02/03/13/15 的 error 码及全部操作（AC-06/06b 为构造隔离、无 error 码）。CLI 命令/退出码映射随 e2e 覆盖。
- `extension protocols sign as documented` — 断言 Role / Scheduler / StopCondition / Consumer 四个协议的签名与 `contracts/public-api.md` §4、ADR-0002 一致（AC-14 的契约侧）。

## Edge cases / error paths

每条 error / authorization / invariant AC 都有自己的专属测试行（已在上表列出，不并入 happy path）。边界与失败情形汇总如下，期望结果用大白话写：

- 主题为空（AC-02）→ 期望：启动被阻止，提示主题不能为空，无会话写入。
- 人设去重后不足两位（AC-03）→ 期望：启动被阻止，明确提示至少需要两位参与者。
- 人设缺角色描述（AC-13）→ 期望：拒绝加载，指明必须提供角色描述。
- 生成失败 / 超时 / 空结果（AC-04b）→ 期望：重试若干次仍失败则跳过该参与者并记录，会话继续推进（不卡死）。
- 越界写入（AC-06）→ 期望：越界写入不可达（构造隔离），目标会话桌面保持不变。
- 越界读取（AC-06b）→ 期望：越界读取不可达（构造隔离），目标会话内容不暴露。
- 路由者选人不合法（AC-07b）→ 期望：回退固定轮转并记录本次无效选择。
- 收敛始终不出现（AC-10b）→ 期望：达到最大轮数上限强制结束并标注「未收敛」。
- 停止时恰有在途发言（AC-11b）→ 期望：等在途发言落桌后再结束，该发言不丢失。
- 同轮二次追加（AC-15）→ 期望：阻止并说明本轮的发言名额已用。

> 另有两枚 error 哨兵码（`session.not_found`、`session.invalid_state`）在 `contracts/public-api.md` §5 标注为 `# inferred`（序列缺口，spec §5 未覆盖「对不存在/已结束的会话操作」）。它们只由「public-api surface」契约测试做形态核对，**不**对应任何 AC——是契约层的未决缺口，留待 api 阶段补序列或显式降级。

## Test data

- **Seed strategy:** 复用 `data-model.md` §Test fixtures 的工厂函数（Python，不进 `migrations/`）：`make_session`（构造 `config` 状态 JSON）、`make_persona`（roster 条目）、`make_speech`（发言 content JSON）、`make_memory_entry`（`memory_entries` 行，供存储层测试）。PII 护栏：仅 `example.test` / 占位名。
- **Integration dependency:** 一个**临时真实 SQLite**（临时文件或内存库）——不是 mock 存储。每次测试拉起、用后拆除。LLM 是外部系统（非本特性拥有的存储）：用 weave 的 `FakeLLM`（确定性、离线）跑确定性路径；存储始终真实。每个会话一个独立 `Weave` 实例（ADR-0005），指向该临时库。
- **Cleanup boundary:** per-test——每个测试用全新临时库，teardown 删除，保证各次运行互不干扰（无清理则套件会 flaky 并卡 CI）。

## NFR validation (load)

spec.md §6 中带数字的 NFR → 四条 load/perf/durability 场景（工具仍泛称：仓库已有负载工具，或 e.g. k6 / Locust）：

- **每轮编排开销 p95 ≤ 100 ms** → 场景：用 FakeLLM（LLM 推理零延迟）驱动会话跑 **≥ 100 轮**，统计每轮编排（选下一发言者 → 生成 → 追加桌面 → 判停止，不含 LLM 推理）的耗时分布，断言 **p95 ≤ 100 ms**。
- **读取完整桌面 p95 ≤ 50 ms** → 场景：构造一张含 **≥ 1000 条**发言的桌面，**重复读取 ≥ 50 次**，统计读延迟，断言 **p95 ≤ 50 ms**。
- **并发会话数 ≥ 5 且互不串扰** → 场景：**并行启动 ≥ 5 个会话**各自跑完，断言每个都正常结束、且每场会话的桌面 **0 跨会话串扰**（无他场发言混入、无丢失/重复）。
- **会话可靠性 99.9% 不被意外中断** → 场景：对进行中会话注入**进程崩溃 / LLM 失败 / 超时 / 断连**，断言恢复到中断那一轮、已落桌发言不重放（`resume_session`，ADR-0003），0 丢失/重复。

> 两条带数字的 NFR **不**做 load：**一致性/耐久「0 丢失/重复」**是正确性不变量，由 AC-04/05/09/11b 的集成测试 + 上一条耐久场景覆盖；**可扩展性「0 处内核改动」**是变更范围审查（review 闸门），非运行时测试。

## CI placement

以下为建议，非流水线配置——`implement` 与仓库 CI 负责实际接线：

- **On every PR:** unit + contract + integration + CLI e2e（全部离线、快：FakeLLM + 临时 SQLite）。
- **On schedule / pre-release:** load/perf + durability（慢、对时间敏感、易 flaky，不适合每 PR 跑）。
