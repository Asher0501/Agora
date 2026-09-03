# Tracker — brainstorm

> Status of every task in the epic. `implement` updates `done` as it commits each task.
> States: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | 搭建 brainstorm 包骨架与测试骨架 | wiring | Asher | S | — | done |
| T2 | 领域类型 + 错误哨兵 + 四扩展点协议 | domain | Asher | M | T1 | done |
| T3 | 记忆仓储（状态/桌面/私有/事件） | infra | Asher | M | T2 | done |
| T4 | PersonaRole + FakeLLM + 上下文窗口 | infra | Asher | M | T2 | done |
| T5 | 默认扩展（round_robin/fixed_rounds/manual） | app | Asher | S | T2 | done |
| T6 | YAML 配置加载与默认装配 | wiring | Asher | S | T2 | done |
| T7 | 引擎生命周期 + 扩展注册表 | app | Asher | M | T2, T3 | done |
| T8 | 回合编排循环 run_session | app | Asher | L | T7, T5, T4 | done |
| T9 | 路由者调度 + 收敛判定 | app | Asher | M | T8 | done |
| T10 | 手动停止 + 在途安全 | app | Asher | M | T8 | done |
| T11 | CLI create/run/stop/export | ports | Asher | M | T7, T6, T8, T9, T10 | done |
| T12 | 集成/并发/耐久 + NFR 插桩 | tests | Asher | M | T11, T9, T10 | done |
| T13 | README 用法与扩展点说明 | docs | Asher | S | T11 | done |

**Total:** 13 tasks, ~11 person-days — all done.
