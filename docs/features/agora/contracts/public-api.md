---
status: Draft
owner: "Asher"
reviewers: ["Tech Lead", "Security Lead"]
updated_at: "2026-09-06"
feature_size: "L"
target_surfaces: [library-sdk, cli]
---

# Public API — agora

> 本文件是 `agora` 引擎的**库接口契约**（`library-sdk` 表面，ADR-0001）——公开的 Python 签名与类型。它是**派生**产物：从 `data-model.md`（实体与约束）+ `sad.md` §6 序列（错误/分支）+ `spec.md` §4/§5（能力清单）派生，不手写。每个字段的溯源见 [`api-sync-report.md`](./api-sync-report.md)。
>
> CLI 表面另见 [`cli.md`](./cli.md)。本特性**无 backend-service / UI / worker** 表面（ADR-0001），故无 OpenAPI、无 `events.md`；进度事件是进程内观测（§8 Observability），不构成外部消息契约。

## 1. Overview

agora 把 brainstorm 已证明可行的「多角色按序接力 + 共享转录 + 判停 + 持久化恢复」内核抽成**无语义**接力协作库。场景作者用一份声明式 YAML 配置描述场景（角色 + 选人 + 判停 + 产出），发起人提供运行时值启动会话，多个 AI 角色按序接力发言到共享转录；选人者决定下一位发言者、裁判判定收敛、判停方式结束会话，会话可持久化并在崩溃后恢复（spec §1）。

**包形态**（SAD §5）：`agora/` 中性包，单向依赖——领域/内核层零 weave 依赖，`adapter/` 是唯一 weave 集成点，配置全部来自 YAML，零硬编码。`scenarios/brainstorm.yaml` 是第一个纯配置场景（实证零代码扩展）。

### 公开模块地图

| Module | 公开符号 | 契约角色 |
|---|---|---|
| `agora.types` | `Run` `Turn` `Agent` `ScenarioConfig` `RoleConfig` `SelectConfig` `StopConfig` `SummaryConfig` `RuntimeValues` `Verdict` `Recap` `RunOutcome` `Turn` 等 | 中性类型（data-model 实体） |
| `agora.errors` | `DomainError` + 12 个错误码 | 错误信封 `{code, message, details?}` |
| `agora.namespaces` | `run_stream_ns` / `run_state_ns` / `run_events_ns` / `agent_stream_ns` / `agent_state_ns` | 命名空间构造（隔离载体） |
| `agora.atoms` | `LLM` `OutputSpec` `Parsed` `Selector` `Terminator` `StreamStore` `StateStore` `Summarizer` `render` `parse` | 五原子协议 + 产出/解析 |
| `agora.relay` | `relay` | 接力循环（选人→判停→产出→落桌） |
| `agora.session` | `create_run` `resume_run` `stop_run` `read_transcript` | 会话生命周期 + resume + 读转录 |
| `agora.config` | `load_config` `parse_config` `validate_config` | 声明式配置加载 + 校验 |
| `agora.extension` | `register_capability` | 扩展区注册（受控逃生门） |
| `agora.adapter.llm` | `BaseLLM` | LLM 适配（deepseek/anthropic/openai/FakeLLM） |
| `agora.adapter.repository` | `Repository` | `memory_entries` 持久化适配（唯一 weave 集成点） |

> `agora.errors` 与 `agora.namespaces` 不在 SAD §5 目录树显式列出，但为 SAD §8 交叉关注（Error handling / ID strategy）的自然落点，镜像 brainstorm 的 `business/errors.py` + `business/namespaces.py`——见报告 §B 结构项。

## 2. Types（`agora.types`）

中性类型：Session/Speech/Persona 已中性化为 Run/Turn/Agent（SAD §2「命名中性化」，data-model 本轮确认）。类型用 dataclass（frozen），零 weave 依赖。

```python
from dataclasses import dataclass, field
from typing import Any, Literal

RunStatus   = Literal["running", "stopped"]
SelectKind  = Literal["round_robin", "llm_pick"]
StopKind    = Literal["fixed_rounds", "llm_verdict", "manual"]
OutputKind  = Literal["free_text", "pick_next", "verdict"]
Termination = Literal["converged", "fixed_rounds", "cap_unconverged", "manual"]
```

### 2.1 场景配置（`ScenarioConfig` 及其部件）

```python
@dataclass(frozen=True)
class RoleConfig:
    id: str                     # 角色 id（config.scenario.roles[].id）
    prompt: str                 # 产出模板；占位符 {name} {role_description} {stance} {topic} {history}
    inject: list[str] = field(default_factory=list)   # 只注入列出的上下文字段
    window: int = 0             # history 截断条数
    output: OutputKind = "free_text"                  # free_text | pick_next | verdict

@dataclass(frozen=True)
class SelectConfig:
    type: SelectKind            # round_robin | llm_pick
    role: str | None = None     # 仅 llm_pick：由哪个角色选人

@dataclass(frozen=True)
class StopConfig:
    type: StopKind              # fixed_rounds | llm_verdict | manual
    max: int | None = None      # fixed_rounds 的轮数 / llm_verdict 的兜底上限
    judge: str | None = None    # 仅 llm_verdict：由哪个角色裁决

@dataclass(frozen=True)
class SummaryConfig:
    role: str                   # 为哪个角色摘要（写入其私有 state，AC-12 / US-06）
    key: str                    # 写入该角色私有 state 的键（如 summary）
    window: int = 20            # 摘要窗口条数（压缩最近 N 条共享转录）

@dataclass(frozen=True)
class ScenarioConfig:
    scenario: str               # 场景名
    roles: list[RoleConfig]
    select: SelectConfig
    stop: StopConfig
    summary: SummaryConfig | None = None
```

### 2.2 运行时值与会话实体

```python
@dataclass(frozen=True)
class RuntimeValues:
    topic: str                              # 主题（AC-02b：缺主题拒绝启动）
    stance: str | None = None               # 立场（辩论场景注入）
    extra: dict[str, Any] = field(default_factory=dict)  # 其余运行时值，逐场注入

@dataclass(frozen=True)
class Run:                                  # 聚合根（data-model RUN）
    run_id: str                             # uuid4，中性 id（SAD §8 ID strategy）
    scenario: ScenarioConfig                # 创建时配置快照（ADR-0006，不可变）
    runtime: RuntimeValues
    status: RunStatus = "running"
    current_seq: int = 0                    # 下一 turn 的序号，单调递增
    verdict: Verdict | None = None          # 仅裁判收敛路径（AC-08）
    recap: Recap | None = None              # 任意终止路径（AC-08/09/10b/11）
    created_at: float = 0.0

@dataclass(frozen=True)
class Turn:                                 # data-model TURN
    run_id: str
    seq: int                                # 显式 run 内单调序号（追加顺序不变量的载体）
    agent_id: str                           # 发言者（系统标注，AC-05）
    text: str
    created_at: float = 0.0

@dataclass(frozen=True)
class Agent:                                # data-model AGENT（物化自 config.roles[]）
    run_id: str
    agent_id: str
    role_description: str                   # config.scenario.roles[].prompt（及注入后描述）

@dataclass(frozen=True)
class Verdict:                              # data-model RUN.verdict
    converged: bool
    conclusion: str | None

@dataclass(frozen=True)
class Recap:                                # data-model RUN.recap
    termination: Termination                # converged | fixed_rounds | cap_unconverged | manual
    recap: str

@dataclass(frozen=True)
class RunOutcome:                           # 终止产物（US-02）
    run_id: str
    status: RunStatus
    verdict: Verdict | None
    recap: Recap
    transcript: list[Turn]
```

## 3. Errors（`agora.errors`）

统一信封 `{code, message, details?}`。`code` 用中性 `agora.*` snake_case（SAD §2/§8「错误码中性化，取代 brainstorm 的 `session.*`」）；`message` 中文可读；`details` 可选。

```python
class DomainError(Exception):
    def __init__(self, code: str, message: str, details: Any = None): ...
    code: str
    message: str
    details: Any | None
    def to_dict(self) -> dict[str, Any]: ...   # {"code","message"[, "details"]}
```

| 错误码 | 触发条件 | 来源 |
|---|---|---|
| `agora.unknown_capability` | 配置引用「闭集菜单 ∪ 已注册扩展」之外的选人/判停方式 | AC-03（Flow 2） |
| `agora.role_description_required` | 某角色缺少产出所需描述 | AC-04（Flow 2） |
| `agora.output_judge_mismatch` | 裁判产出格式与「判定收敛」所需不符（如 free_text 却要 verdict） | AC-13（Flow 2） |
| `agora.scenario_not_found` | 启动引用不存在的场景 | AC-02b（Flow 3） |
| `agora.runtime_value_required` | 运行时值非法（如缺主题） | AC-02b（Flow 3） |
| `agora.run_not_found` | 恢复/停止/读一个不存在的会话 | AC-15b（Flow 10） |
| `agora.run_corrupted` | 恢复损坏的会话 | AC-15b（Flow 10） |
| `agora.invalid_state` | 对已结束的会话继续接力 | Flow 1（镜像 brainstorm `session.invalid_state`） |
| `agora.turn_already_produced` | 同一 turn 二次产出 | AC-06（Flow 6） |
| `agora.reserved_agent_id` | 角色 id 取保留字 `events`（与系统事件 namespace 撞名） | 加载时校验（Flow 2） |
| `agora.invalid_placeholder` | 模板占位符与 inject 字段名不匹配，或缺失字段未注入 | 加载时校验（Flow 2） |
| `agora.invalid_config` | 配置结构/数值非法（max/window 非整数、judge/picker 引用不存在的角色等） | 加载时校验（Flow 2） |

**不在错误码里**（记录性，非拒绝）：

- 跨会话/角色隔离（AC-16/17）是**结构性**（namespace 构造）而非运行时拒绝——读路径只带本 agent/run 的 namespace，越界数据不可见。故不设 `cross_namespace_*` 哨兵（镜像 brainstorm）。
- 系统观测事件 `invalid_choice`（AC-07b）与 `verdict_parse_failure`（OQ4）是落盘 stream 记录（data-model §System records），**不是** `DomainError`。

> `agora.*` 是**新包**的错误码提案（SAD §8）；仓库内现仅有 brainstorm 的 `session.*` 登记。本契约按 1:1 中性化映射，落地时在 `agora/errors.py` 一并建立登记表——见报告 §B 点 2。

## 4. Atoms（`agora.atoms`）与扩展区

五个原子（ADR-0003 闭集菜单）：**产出**（render + LLM + parse）、**选人**、**判停**、**存储**、**摘要**。「新能力 = 新原子 = 写代码」；菜单之外走扩展区（ADR-0004）。

```python
from typing import Protocol

# ① LLM —— 唯一能力原子
class LLM(Protocol):
    async def complete(self, prompt: str) -> str: ...

# ② 模板渲染 —— 注入上下文字段 + 截断 history 到 window 条
def render(template: str, ctx: dict[str, Any], window: int) -> str: ...

# ③ 输出解析 —— 按声明格式解读 LLM 输出
@dataclass(frozen=True)
class OutputSpec:
    kind: OutputKind  # free_text → 原文；pick_next → NEXT:<id>|CONVERGE:<结论>；verdict → CONVERGE:<结论>|CONTINUE

@dataclass(frozen=True)
class Parsed:
    text: str | None = None          # free_text 原文
    next_agent_id: str | None = None # pick_next 命中
    converged: bool = False          # pick_next/verdict 命中 CONVERGE
    conclusion: str | None = None
    parse_failure: bool = False      # 解析失败（OQ4 → 视为未收敛 + 观测事件）

def parse(text: str, spec: OutputSpec) -> Parsed: ...

# ④ 选人 —— selector 原子（闭集：round_robin / llm_pick）
@dataclass(frozen=True)
class Selection:
    agent_id: str | None = None
    converged: bool = False
    conclusion: str | None = None
    invalid_choice: str | None = None   # AC-07b：选定的下一位不在名单内

class Selector(Protocol):
    async def next(self, roster: list[Agent], transcript: list[Turn]) -> Selection: ...

# ⑤ 判停 —— terminator 原子（闭集：fixed_rounds / llm_verdict / manual）
@dataclass(frozen=True)
class StopDecision:
    stop: bool
    termination: Termination | None = None  # converged | fixed_rounds | cap_unconverged | manual
    converged: bool = False
    conclusion: str | None = None

class Terminator(Protocol):
    async def should_stop(self, ctx: dict[str, Any]) -> StopDecision: ...

# ⑥ 摘要 —— summary 原子（US-06 / AC-12）
class Summarizer(Protocol):
    async def summarize(self, transcript: list[Turn], ctx: dict[str, Any]) -> str: ...
```

**闭集原子清单**（场景按名引用，来自 atomic-relay §1 + SAD §4）：

| 原子 | 类别 | 语义 |
|---|---|---|
| `round_robin` | selector | 按 roster 顺序循环（正反交替 = 2 人轮转） |
| `llm_pick` | selector | 让某角色选下一位（`pick_next` 输出） |
| `fixed_rounds` | terminator | 发言数达 `max` 停止（纯状态函数，不调 LLM） |
| `llm_verdict` | terminator | 让某角色裁决收敛（`verdict` 输出），`max` 兜底 |
| `manual` | terminator | 收到停止指令停止（进程内） |

### 扩展区（`agora.extension`）

```python
def register_capability(registry, name: str, capability) -> None: ...
```

- 扩展先注册、后加载（ADR-0005）；「已知能力」= 闭集菜单 ∪ 已注册扩展，未注册即拒。
- 信任边界（ADR-0004）：同进程、视为受信代码，读范围以 AC-16/17 为界（不跨 namespace）；本轮**不承诺稳定/版本化 ABI**。

## 5. Engine API（`agora.session` + `agora.relay`）

```python
async def create_run(repository, scenario: ScenarioConfig, runtime: RuntimeValues) -> Run:
    """校验（AC-03/04/13）+ 快照 config（ADR-0006）+ 建 running Run（AC-02）。"""

async def resume_run(repository, run_id: str) -> Run:
    """从快照 + 已落桌转录重建 Run（ADR-0006）；不存在→agora.run_not_found（AC-15b）。"""

async def relay(repository, registry, run_id: str) -> RunOutcome:
    """接力循环：每轮 选人→判停→（未停才）产出→落桌（ADR-0007，Flow 1）。"""

async def stop_run(repository, registry, run_id: str) -> RunOutcome:
    """手动停止：取消在途生成、该发言不落桌（AC-11，Flow 8）。"""

async def read_transcript(repository, run_id: str) -> list[Turn]:
    """读共享转录，按 seq 升序（data-model §TURN access pattern）。"""

def subscribe(registry, observer: Observer) -> None:
    """订阅进度事件（AC-18，进程内；Flow 11）。"""
```

**接力循环顺序**（ADR-0007）：每轮 `选人 → 判停（fixed_rounds 数条数 / llm_verdict 轮首调 judge / manual 查停止标志）→ 未停才产出并落桌`。收敛或达上限时绝不额外多产一条（AC-09/AC-10b）。

## 6. Config（`agora.config`）

```python
def load_config(path: str | Path) -> ScenarioConfig:        # 从 YAML 读 + 校验
def parse_config(raw: dict[str, Any]) -> ScenarioConfig:    # 从映射解析 + 校验
def validate_config(config: ScenarioConfig) -> None:        # 校验不变量，非法即 raise DomainError
```

**加载时校验面**（ADR-0005，US-07）：能力 ∈ 菜单 ∪ 已注册扩展（AC-03）、角色描述必填（AC-04）、output 与 select/stop 匹配（AC-13）、模板占位符与 inject 字段名。非法配置 100% 加载时拒绝 + 可读原因（哪个角色缺什么 / 哪个能力不受支持）。

## 7. Store（`agora.store`）与命名空间（`agora.namespaces`）

```python
class StreamStore(Protocol):              # append-only
    async def append(self, ns: str, entry: dict[str, Any]) -> None: ...
    async def read(self, ns: str) -> list[dict[str, Any]]: ...

class StateStore(Protocol):               # keyed 状态
    async def get(self, ns: str, key: str) -> Any | None: ...
    async def set(self, ns: str, key: str, value: Any) -> None: ...
```

命名空间构造（data-model §Namespace scheme，中性根 `agora:`）：

```python
def run_stream_ns(run_id: str) -> str:                 # agora:{run_id}:stream        共享转录
def run_state_ns(run_id: str) -> str:                  # agora:{run_id}:state         run 状态
def run_events_ns(run_id: str) -> str:                 # agora:{run_id}:events:stream 系统观测事件
def agent_stream_ns(run_id: str, agent_id: str) -> str:  # agora:{run_id}:{agent_id}:stream   agent 私有便签
def agent_state_ns(run_id: str, agent_id: str) -> str:   # agora:{run_id}:{agent_id}:state    agent 私有 keyed 状态
```

run 状态 key（data-model §RUN）：`STATE_KEY_CONFIG = "config"`、`STATE_KEY_STATUS = "status"`、`STATE_KEY_VERDICT = "verdict"`、`STATE_KEY_RECAP = "recap"`。保留段 `events` 不得作为 `agent_id`（配置校验列为保留字，data-model §Namespace scheme）。

## 8. Observability（进度事件，进程内）

```python
@dataclass(frozen=True)
class ProgressEvent:
    name: str
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)

class Observer(Protocol):
    def on_event(self, event: ProgressEvent) -> None: ...
```

| 事件名 | 时机 | 来源 |
|---|---|---|
| `run.turn_started` | 回合开始 | Flow 11 / SAD §8 |
| `run.turn_landed` | 发言落桌 | Flow 11 / SAD §8 |
| `run.converged` | 裁判宣告收敛 | Flow 11 / SAD §8 |
| `run.stopped` | 停止 | Flow 11 / SAD §8 |

**隔离**（AC-18）：事件只携带本 run（本 namespace）内容，不含他会话转录摘录或私有状态。**无 schema 版本化、无幂等键/重试/死信**（SAD §6 flagged items——本地单进程同步编排，非消息队列）。

## 9. Stability / versioning

- `agora` 包 semver `0.1.0`（对齐 weave 0.1.0 / brainstorm 0.1.0，SAD §2）。版本由 CHANGELOG 显式推进，本契约不静默 bump。
- **扩展区 ABI 本轮不承诺稳定/版本化**（ADR-0004，SAD §11 accepted debt）——自定义能力视为「内部逃生门」。
- 进度事件**无 schema 版本化**（SAD §11 accepted debt）。
- 破坏性变更：旧 brainstorm 会话数据不迁移（spec §3）；brainstorm 的 `session.*` 错误码 / `brainstorm:`/`persona:` 命名空间 / Session/Speech/Persona 类型全部中性化为 `agora.*` / `agora:*` / Run/Turn/Agent（ADR-0002）。
