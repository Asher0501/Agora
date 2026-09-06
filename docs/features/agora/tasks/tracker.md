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

**Total:** 15 tasks, ~17 person-days（单人 Asher；L 规模，约 3–4 周）。
