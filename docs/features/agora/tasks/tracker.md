# Tracker — agora

> Status of every task in the epic. `implement` updates `done` as it commits each task.
> States: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | 中性领域类型、错误码、命名空间 | domain | Asher | M | — | done |
| T2 | 五原子协议 + 产出/解析 + 菜单原子 | domain | Asher | M | T1 | done |
| T3 | SQLite Repository 适配 | infra | Asher | M | T1, T2 | done |
| T4 | LLM 适配 | infra | Asher | S | T2 | done |
| T5 | 配置 schema + 加载校验 | app | Asher | M | T1, T2 | done |
| T6 | 扩展区注册 | app | Asher | S | T2 | done |
| T7 | 接力循环 | app | Asher | L | T2, T3, T4, T6 | done |
| T8 | 会话生命周期 | app | Asher | M | T1, T3, T5 | done |
| T9 | 摘要原子 | app | Asher | M | T2, T5, T7 | done |
| T10 | CLI 命令 | ports | Asher | M | T7, T8, T5 | done |
| T11 | 包装配 + DI | wiring | Asher | S | T3–T10 | done |
| T12 | brainstorm.yaml | docs | Asher | S | T5, T2 | done |
| T13 | brainstorm 迁移 | wiring | Asher | M | T11, T12 | done |
| T14 | brainstorm 58 测试回归 | tests | Asher | L | T13 | done |
| T15 | NFR/一致性/并发测试 | tests | Asher | M | T11 | done |
| T16 | 修复 AC-06 同 turn 守卫 | infra | Asher | S | — | done |
| T17 | 修复 AC-11 停止握手 | app | Asher | M | — | done |
| T18 | 接通 AC-14 扩展区 | app | Asher | S | — | done |
| T19 | 对齐 AC-18 observe | ports | Asher | S | — | done |
| T20 | 失控守卫（封顶+max必填） | app | Asher | M | — | done |
| T21 | 配置标量类型校验 | app | Asher | S | T20 | done |
| T22 | 声明 weave-agent-sdk | wiring | Asher | S | — | done |
| T23 | 文档漂移收口 | docs | Asher | S | — | done |
| T24 | 测试缺口补全 | tests | Asher | M | T20 | done |
| T25 | 修复 prompt 渲染机制 | app | Asher | M | — | done |
| T26 | 收口契约文档漂移 | docs | Asher | S | — | done |
| T27 | 补 CLI stop/resume 测试 | tests | Asher | S | — | todo |
| T28 | 配置结构形状守卫 | app | Asher | S | T25 | todo |
| T29 | llm_verdict/llm_pick 必填 judge/role | app | Asher | S | T25 | todo |

**Total:** 29 tasks（T16–T24 为 review 反馈的 14 项修复；T25–T29 为复评 r2 反馈的 6 项修复）。
