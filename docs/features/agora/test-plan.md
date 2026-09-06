---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-06"
feature_size: "L"
---

# Test plan — agora

> 把 spec.md §5 的 21 个验收标准（AC）映射为可执行的测试层级（unit / integration / contract / e2e / load），并定下集成依赖、测试数据与清理边界、负载场景与 CI 排布。`implement` 照着这张表写红测试，而不是「看情况」。

## Levels

<!-- 本特性 surface = [library-sdk, cli]（sad.md frontmatter），无 UI 表面 → 不加 component / visual-regression / e2e-through-UI 三个前端层级。 -->

| Level | Scope | Strategy (generic — no tool names) |
|---|---|---|
| Unit | 纯逻辑：一条规则、一个计算、一个校验器——无 I/O | 内存中运行，无外部依赖 |
| Integration | 模块对着它拥有的真实依赖（store / LLM 适配） | 即弃临时 SQLite 文件（真 weave schema、真写路径）+ 确定性离线 LLM（仓库自带的 FakeLLM） |
| Contract | 两个参与者之间的边界——公开 API 形状或事件 schema | 用真实形状对约定契约做校验，不手写桩 |
| E2E | 一条完整流程端到端（每个关键用户故事一条） | 走真实入口（CLI 命令或库公开 API），对即弃依赖 |
| Load | 仅当 NFR 带数字时的校验 | 仓库已有的负载/插桩手段，或 k6 / Locust 这类通用工具 |

<!-- Component / Visual-regression / E2E-through-UI：N/A（target_surfaces 无 UI 表面，本迭代是 library-sdk + cli）。 -->

## AC coverage

<!-- 每个 spec.md §5 AC → ≥1 测试行。一个 AC 可拆成多行（规则做 unit、流程做 e2e）。零未覆盖 AC。测试名取自 AC 意图，非框架约定。期望结果用白话，无状态码、无错误码串、无 SQL。 -->

| AC (spec.md §5) | Test name (intent-based) | Level | Expected outcome |
|---|---|---|---|
| AC-01 <happy path> | brainstorm-scenario-runs-with-zero-engine-code | e2e | 用纯配置跑通 brainstorm 能力集合，全程零引擎代码改动 |
| AC-02 <happy path> | start-session-records-scenario-and-runtime | integration | 创建会话、记录场景与运行时值、状态置为运行中并确认已开始 |
| AC-02 <happy path> | start-session-via-cli-run | e2e | `run` 命令启动会话，返回 run_id 并确认会话已开始 |
| AC-02b <error> | missing-topic-is-rejected | unit | 缺主题的运行时值被拒，说明缺哪个运行时值 |
| AC-02b <error> | unknown-scenario-is-rejected | integration | 引用不存在的场景被拒，说明该场景不存在 |
| AC-03 <error> | unknown-select-or-stop-capability-is-rejected | unit | 引用「菜单∪已注册扩展」之外的选人/判停被拒，说明该方式不受支持 |
| AC-04 <error> | role-missing-description-is-rejected | unit | 缺产出描述的角色被拒，说明哪个角色缺什么 |
| AC-05 <happy path> | turn-produces-context-aware-speech | integration | 产出一条承接主题与历史的发言，记为下一条并按序标注发言者 |
| AC-05 <happy path> | produce-atom-renders-and-parses | unit | 模板渲染 + 输出解析对三种输出格式正确，解析失败返回失败哨兵 |
| AC-06 <domain invariant> | second-produce-in-same-turn-is-blocked | integration | 同一 turn 二次产出被阻止，不产生第二条（每 turn 恰好一条） |
| AC-07 <happy path> | selector-invoked-to-pick-next-speaker | integration | 路由时点请选人者选定下一位发言者 |
| AC-07b <domain invariant> | invalid-selection-retries-then-falls-back | integration | 无效选择重试 1 次，仍无效回退到角色名单顺序选取，每次无效记观测事件 |
| AC-07b <domain invariant> | resolve-selection-given-roster | unit | 给定选人结果与角色名单，正确判定有效/无效并产出回退顺序 |
| AC-08 <happy path> | judge-convergence-ends-with-verdict-and-recap | integration | 裁判宣告收敛 → 结束会话、产出总结并附裁判结论 |
| AC-09 <happy path> | fixed-rounds-stops-without-extra-speech | integration | 达固定条数 → 自动结束、产出总结，不额外多产出一条发言 |
| AC-09 <happy path> | fixed-rounds-counting | unit | 计数逻辑在产出前正确判定达阈值 |
| AC-10b <domain invariant> | cap-forces-end-labelled-unconverged | integration | 裁判未收敛达条数上限 → 强制结束、总结标注「未收敛」 |
| AC-11 <happy path> | manual-stop-cancels-in-flight-and-recaps | integration | 取消在途生成（该发言不落桌）、结束并产出标注「手动停止」的总结 |
| AC-11 <happy path> | stop-via-cli-stop | e2e | `stop` 命令取消在途、返回标注手动停止的总结 |
| AC-12 <happy path> | summary-persists-and-drives-next-turn | integration | 摘要写入角色私有状态，下轮该角色读到自己摘要并据此发言 |
| AC-13 <cross-context> | judge-output-mismatch-rejected | unit | 裁判产出格式与「判定收敛」不符的配置被拒并说明不匹配 |
| AC-14 <happy path> | extension-capability-takes-effect-menu-untouched | integration | 自定义能力在场景中生效，标准菜单与引擎其余部分不受影响 |
| AC-14 <happy path> | register-capability-before-load | unit | 先注册后加载；未注册的能力被拒 |
| AC-15 <happy path> | resume-restores-landed-turns-and-private-state | integration | 恢复到中断轮，已落桌不重放不丢失，私有状态一并恢复，在途丢弃该轮重试 |
| AC-15 <happy path> | resume-via-cli-resume | e2e | `resume` 命令恢复并继续接力循环 |
| AC-15b <error> | resume-missing-or-corrupt-is-rejected | integration | 不存在/损坏的会话恢复被拒并说明原因 |
| AC-16 <authorization> | agent-cannot-read-other-session-or-role-state | integration | 角色读他会话转录/他角色私有状态被拒，不暴露 |
| AC-17 <authorization> | host-cannot-read-other-hosts-session | integration | 发起人读他人会话转录/私有状态被拒，不暴露 |
| AC-18 <progress events> | progress-events-carry-only-own-namespace | unit | 事件过滤只保留本会话（本 namespace）内容 |
| AC-18 <progress events> | progress-event-shape-matches-agreed-schema | contract | 事件形状符合约定 schema（回合开始 / 发言落桌 / 收敛 / 停止） |
| AC-18 <progress events> | observe-via-cli-observe | e2e | `observe` 命令流式打印本会话事件，不含他会话内容 |

> 补充表面契约（非 §5 AC，但同属 contract 层）：库公开 API（`agora/__init__.py` 导出形状）对 `contracts/public-api.md`、CLI 命令/标志/退出码对 `contracts/cli.md` 做形状校验——由 T10/T11 落位，不进上表。

## Edge cases / error paths

<!-- 每个 error / authorization AC 已有自己的专属行（上表），不并入 happy path。以下是 spec 隐含、但未单独成 AC 的边界与失败路径。 -->

- 裁判产出解析失败（不含预期格式）→ 确定性回退：视为不收敛 + 记录观测事件（不污染共享转录）。
- 角色 id 取保留字 `events` → 加载时被拒（与系统事件 namespace 撞名）。
- 配置占位符 / `inject` 引用不存在的角色或变量 → 加载时被拒并说明缺什么。
- 主题注入（恶意主题诱导角色泄露系统提示或他会话内容）→ 主题按不可信数据处理；跨会话 namespace 隔离（AC-16/17）兜底。
- 生成失败 / 超时 / 空结果 → spec §11 记为「语义未定，留 implement」，本条仅标记、不写断言（不臆造行为）。

## Test data

- Seed strategy：工厂函数贴合 data-model.md 实体（`make_run` / `make_agent` / `make_turn` / `make_memory_entry`），PII 护栏仅 `example.test` / 占位名。
- Integration dependency：即弃临时 SQLite 文件（真 `memory_entries` schema、真读写路径），**不 mock 数据存储**；LLM 用仓库自带的确定性离线实现（FakeLLM）。
- Cleanup boundary：per-test 临时库（每个测试/套件独享一个 temp DB，跑完删除），保证各 run 独立、无状态泄漏。

## NFR validation (load)

<!-- 每个带数字的吞吐/延迟 NFR 一个场景。耐久/一致性类 NFR（可靠性、0 丢失）不走 load，见下注。 -->

- 每轮编排开销（不含生成）p95 ≤100 ms → 场景：单场 N=50 条发言的会话（离线 LLM 使生成近零，隔离编排开销），持续整场，断言每轮编排 p95 ≤100 ms。
- 读取完整共享转录 p95 ≤50 ms → 场景：对已落桌 200 条发言的转录重复读 100 次，断言读完整转录 p95 ≤50 ms。
- ≥5 并发会话隔离 + 不劣化 ≤2× → 场景：5 个会话并发各跑 30 条发言，断言数据隔离（AC-16/17）且并发下每轮编排 p95 ≤200 ms（≤2× 单会话基线）。

> 耐久/一致性类 NFR 不进 load 节：≥99.9% 不中断、0 丢失/0 重复、非法配置 100% 拒绝，在 integration 层以耐久/追加顺序不变量测试落地（T15）。

## CI placement

<!-- 建议，非流水线配置——implement 与仓库 CI 负责实际接线。 -->

- On every PR：unit + contract + integration（临时 SQLite 快、无需容器）。
- On schedule / pre-release：e2e（CLI 全链路）+ load（延迟/并发场景）；耐久（可靠性/一致性）随 integration 或独立耐久 job 跑。
