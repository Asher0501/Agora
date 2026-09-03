---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead"]
updated_at: "2026-09-03"
feature_size: "M"
---

# 设计草案 — 原子接口 + 声明式配置（agora 引擎，原 atomic relay）

> 目的：把「会重复出现的能力」固化成少量**原子接口**（代码，写一次），把「多变的内容」（prompt、立场、上下文、组合、输出格式）全部压成**声明式配置**。能力集合相同的场景之间，切换成本趋近于零；只有引入全新能力时才动一次代码。
>
> 这是对 ADR-0002「最小内核 + 可插拔扩展点」的**细化/覆盖**——四个扩展协议（Role/Scheduler/StopCondition/Consumer）从「Python 协议 + 各自实现」降维成「配置 + 少量选择器/终止器原子」。落地前需固化为 Accepted ADR 并回改 sad.md §5。

## 1. 原子接口层（代码，写一次）

```python
# ① LLM 调用 —— 唯一的能力原子（新能力 = 新增同层原子，如 lookup(query)）
class LLM(Protocol):
    async def complete(self, prompt: str) -> str: ...

# ② 模板渲染 —— 把上下文字段 + 历史窗口拼进 prompt
def render(template: str, ctx: dict, window: int) -> str:
    """ctx 里 history 截断到最近 window 条，再按 {field} 占位符替换。"""

# ③ 输出解析 —— 按声明的格式解读 LLM 输出
@dataclass(frozen=True)
class OutputSpec:
    kind: Literal["free_text", "pick_next", "verdict"]
    # free_text: 原文照收
    # pick_next: NEXT:<id> | CONVERGE:<结论>
    # verdict:   CONVERGE:<结论> | CONTINUE
def parse(text: str, spec: OutputSpec) -> Parsed: ...

# ④ 接力循环 —— 有序、持久化、崩溃恢复、在途停止（L1 的重活都在这里）
async def relay(
    roster: list[Participant],
    selector: Selector,        # round_robin | llm_pick
    producer: Producer,        # = render + llm + parse，按 role 配置驱动
    terminator: Terminator,    # fixed_rounds | llm_verdict | manual
    observers: list[Observer],
) -> Transcript: ...

# ⑤ 存储 —— namespace KV（L1 无语义存储）
class StreamStore(Protocol):
    async def append(self, ns: str, entry: dict) -> None: ...
    async def read(self, ns: str) -> list[dict]: ...
class StateStore(Protocol):
    async def get(self, ns: str, key: str) -> Any | None: ...
    async def set(self, ns: str, key: str, value: Any) -> None: ...
```

**选择器/终止器原子清单**（闭集，场景按名引用）：

| 原子 | 类型 | 语义 |
|---|---|---|
| `round_robin` | selector | 按 roster 顺序循环（正反交替 = 2 人轮转，复用） |
| `llm_pick` | selector | 让某角色选下一位（`pick_next` 输出） |
| `fixed_rounds` | terminator | 发言数达 `max` 停止（纯状态函数，不调 LLM） |
| `llm_verdict` | terminator | 让某角色裁决收敛（`verdict` 输出），`cap` 兜底 |
| `manual` | terminator | 收到停止指令停止（进程内） |

## 2. 配置 schema（声明式）

```yaml
scenario: <name>

roles:                          # producer = 模板 + 注入字段 + 输出格式
  - id: <str>
    prompt: <template>          # 占位符 {name} {role_description} {stance} {topic} {history}
    inject: [topic, history, stance, ...]   # 只注入列出的上下文字段
    window: <int>               # history 截断条数（对应 review finding 6）
    output: free_text | pick_next | verdict

select:
  type: round_robin | llm_pick
  role: <role_id>               # 仅 llm_pick：由哪个角色选人

stop:
  type: fixed_rounds | llm_verdict | manual
  max: <int>                    # fixed_rounds 的轮数 / llm_verdict 的兜底上限
  judge: <role_id>              # 仅 llm_verdict：由哪个角色裁决
```

`topic` 与 `stance` 等**运行时值**由每场会话注入（不走 YAML 硬编码），对应现在 `SessionConfig` 的角色。

## 3. 场景 A —— 头脑风暴（配置）

```yaml
scenario: brainstorm
roles:
  - id: skeptic
    prompt: "你是{name}。{role_description}\n主题：{topic}\n已有讨论：{history}\n请围绕主题提出你的想法。"
    inject: [topic, history]
    window: 20
    output: free_text
  - id: optimizer
    prompt: "你是{name}。{role_description}\n主题：{topic}\n已有讨论：{history}\n请提出改进或补充。"
    inject: [topic, history]
    window: 20
    output: free_text
  - id: devil
    prompt: "你是{name}。{role_description}\n主题：{topic}\n已有讨论：{history}\n请找出风险与漏洞。"
    inject: [topic, history]
    window: 20
    output: free_text
select: { type: round_robin }
stop:  { type: fixed_rounds, max: 12 }
```

## 4. 场景 B —— 辩论（配置）

```yaml
scenario: debate
roles:
  - id: affirmative
    prompt: "你是正方。立场：{stance}\n主题：{topic}\n已有陈词：{history}\n请立论或反驳。"
    inject: [topic, history, stance]
    window: 20
    output: free_text
  - id: negative
    prompt: "你是反方。立场：{stance}\n主题：{topic}\n已有陈词：{history}\n请立论或反驳。"
    inject: [topic, history, stance]
    window: 20
    output: free_text
  - id: judge
    prompt: "你是裁判。已有陈词：{history}\n论点是否已穷尽？穷尽则输出 CONVERGE:<胜方>，否则输出 CONTINUE。"
    inject: [history]
    window: 0
    output: verdict
select: { type: round_robin }              # 正反交替 = 2 人轮转
stop:  { type: llm_verdict, judge: judge, max: 20 }
```

## 5. 执行轨迹（证明能跑通）

**一轮的通用流程**（`relay` 内部，与场景无关）：

```
selector.next(roster, log)                    # round_robin → 下一位 id
producer:  render(prompt, ctx, window)        # 注入字段 + 截断 history → prompt
           llm.complete(prompt)               # → text
           parse(text, output)                # free_text → 原文；pick_next/verdict → 结构化
log.append({seq, participant_id, text})       # 追加共享日志（有序、持久化）
terminator.should_stop(state)                 # fixed_rounds → len>=max；llm_verdict → 调 judge
observers.on_event(...)
```

**brainstorm 一轮**：`selector=round_robin` 给 `skeptic` → `render` 注入 `{topic, history[≤20]}` → `llm.complete` → `parse(free_text)` 原文落桌 → `terminator=fixed_rounds` 数到 12 停。✓ 跑通。

**debate 一轮**：`selector=round_robin` 在 `[affirmative, negative]` 间交替 → `render` 多注入 `{stance}` → `llm.complete` → 落桌 → `terminator=llm_verdict` 每次调 `judge`（`render` 注入 `{history}`，`parse(verdict)` 得 `CONVERGE:<胜方>` 或 `CONTINUE`），`CONVERGE` 即停、`max:20` 兜底。✓ 跑通。

**关键**：两场景共用同一套原子代码，`relay`/`render`/`parse`/`llm`/`store` **零改动**，差异只在 YAML 的 `prompt`/`inject`/`select`/`stop` 四栏。

## 6. 与现状的映射（ADR-0002 的四个协议 → 原子 + 配置）

| 现状（business/protocols.py） | 新设计 | 变化 |
|---|---|---|
| `Role` 协议 + `PersonaRole` 实现 | `roles[].prompt/inject/window/output` 配置 + render/parse 原子 | **协议 → 配置** |
| `Scheduler` 协议 + round_robin/moderator | `select.type` 引用 `round_robin` / `llm_pick` 原子 | 协议 → 原子 |
| `StopCondition` 协议 + fixed/convergence/manual | `stop.type` 引用 `fixed_rounds`/`llm_verdict`/`manual` 原子 | 协议 → 原子 |
| `Consumer` 协议 | `observers` 原子（不变） | 保持 |
| `engine/loop.py`（带 brainstorm 语义） | `relay()`（无语义） | **重构为 L1** |
| `repository.py`（揉 L1+L2） | `StreamStore`/`StateStore`（L1）+ 语义映射（L2） | 拆层 |

**吸收的 review findings**：`window` 字段 = finding 6；`inject` 可含私有笔记/stance = finding 7；config schema 校验（枚举/max>0）= finding 5。

## 7. 边界与代价（诚实记录）

1. **配置只能组合已有原子**：新「能力」（调 LLM 之外的 `lookup`/`tool.call`/`search`）= 新原子 = 写代码。能力集合相同的场景才是纯配置。
2. **别让配置膨胀成 DSL**：一旦 prompt/`inject` 需要表达条件、循环、多步推理，就该写代码，而不是给 schema 加控制流。
3. **「moderator = 选人 + 收敛」被拆成两个原子**（`llm_pick` selector + `llm_verdict` terminator）——与现行 AC-07/08（路由者既选下一位又判收敛）需重新对齐：要么接受拆分（更干净），要么保留一个组合原子。
4. **破坏性变更**：现有 `Role/Scheduler/StopCondition` 三个 Python 协议对扩展方是破坏性变更；需在新 ADR 里写明迁移与兼容策略。
5. **配置校验面扩大**：template 占位符、inject 字段名、output 与 select/stop 的匹配都需要 schema 校验（对应 review finding 5）。

## 8. 落地路径（建议）

1. 固化 ADR-0007（覆盖 ADR-0002），sad.md §5 分层图改为「原子接口层 + 声明式配置层」。
2. 先抽 `relay()` + `render/parse` + `store` 五个原子，用 brainstorm 场景回归现有 58 测试（绿）。
3. 再把 brainstorm 的 `roles/select/stop` 声明化为上面 YAML，跑通。
4. 加 debate 场景 YAML 作为「零代码扩展」的验收样例（对应 AC-14 的扩展性证明）。
