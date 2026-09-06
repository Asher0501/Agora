---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-06"
feature_size: "L"
target_surfaces: [library-sdk, cli]
---

# CLI — agora

> 命令行驱动器契约（`cli` 表面，ADR-0001）。`agora` 是发起人（Host）在本地单进程运行的命令行工具：启动/停止/恢复/观察一场会话（SAD §5 `cli/`：`run/stop/resume/observe`）。命令/标志/退出码派生自 `spec.md` §4/§5 + `sad.md` §6 序列 + `public-api.md`，不手写。
>
> 库表面另见 [`public-api.md`](./public-api.md)。字段溯源见 [`api-sync-report.md`](./api-sync-report.md)。

## 1. Invocation

```
agora <command> [options]
```

全局标志：

| 标志 | 值 | 说明 |
|---|---|---|
| `--db <path>` | str | SQLite 库路径（默认 `./agora.db`） |

## 2. Commands

### 2.1 `run` — 启动并跑完一场会话（US-02 / AC-02）

```
agora run --config <scenario.yaml> --topic <str> [--stance <str>] [--db <path>]
```

| 标志 | 必需 | 说明 |
|---|---|---|
| `--config <path>` | 是 | 场景 YAML（roles/select/stop/summary；spec §1「配置 = YAML 数据文件」） |
| `--topic <str>` | 是 | 运行时值：主题（AC-02b 缺主题拒绝启动） |
| `--stance <str>` | 否 | 运行时值：立场（辩论场景注入；spec §1 运行时值不写死进配置） |

**行为**：加载并校验场景配置（Flow 2，AC-03/04/13 非法即拒）→ 校验运行时值（Flow 3，AC-02b）→ 创建会话、定格配置快照（ADR-0006）→ 进入接力循环跑到终止 → 打印 `run_id` 与终止产物（总结 + 裁判收敛时的结论）。

**输出**：先打印 `run_id`，终止后打印 `status=… termination=… converged=… conclusion=… turns=N`。

### 2.2 `stop` — 手动停止（AC-11 / Flow 8）

```
agora stop <run_id> [--db <path>]
```

**行为**：取消当前在途生成（该发言不落桌）、标记会话结束、产出标注「手动停止」的总结。退出码 0；`run_id` 不存在 → 退出码 1（`agora.run_not_found`）。

### 2.3 `resume` — 恢复中断的会话（US-09 / AC-15 / Flow 10）

```
agora resume <run_id> [--db <path>]
```

**行为**：按创建时配置快照重建会话，恢复到中断那一轮；已落桌不重放、不丢失，各角色私有状态一并恢复；崩溃前未落桌的在途发言丢弃、该轮重试（ADR-0006）。`run_id` 不存在 → 退出码 1（`agora.run_not_found`）；状态损坏 → 退出码 1（`agora.run_corrupted`）。

### 2.4 `observe` — 打印已落盘的观测事件（AC-18 / Flow 11）

```
agora observe <run_id> [--db <path>]
```

**行为**：打印本会话已落盘的系统观测事件（`invalid_choice` 无效选择 / `verdict_parse_failure` 裁判解析失败）。进度事件（回合开始 / 发言落桌 / 收敛 / 停止）是进程内发布-订阅（`public-api.md` §8），不持久化、不跨进程，故独立 `observe` 进程打印的是持久化观测事件流，不含他会话转录摘录或私有状态（AC-18）。`run_id` 不存在 → 退出码 1（`agora.run_not_found`）。

## 3. Exit codes

| 码 | 含义 | 触发 |
|---|---|---|
| `0` | 成功 | 命令正常完成 |
| `1` | 领域错误 | `DomainError`（`agora.*` 错误码）→ stderr 打印 `错误：<message>（<code>）` |
| `2` | 用法错误 | 参数缺失/非法（argparse 约定）→ stderr 打印用法 |

## 4. 约定

- **UTF-8**：Windows 控制台强制 UTF-8（镜像 brainstorm，中文不因 cp1252 乱码）。
- **零引擎代码**：`run` 走纯配置路径；菜单外能力经扩展区注册（`public-api.md` §4），CLI 不新增命令。
- **无网络/多副本**：本地单进程，无鉴权、无幂等键、无重试/死信仪式（SAD §6 flagged items）。
