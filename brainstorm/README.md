# brainstorm

多个人设围绕一个主题、按序接力发言、所有发言落到共享桌面的头脑风暴引擎。以 **library-sdk（引擎核心）+ cli（命令行驱动器）** 两个表面交付：稳定内核（会话生命周期、回合编排循环、共享桌面、扩展注册表）+ 四个可插拔扩展点（角色 / 调度策略 / 停止条件 / 消费界面）。

> 设计契约见 [`spec.md`](../docs/features/brainstorm/spec.md)（需求与验收）、[`sad.md`](../docs/features/brainstorm/sad.md)（架构）、[`data-model.md`](../docs/features/brainstorm/data-model.md)（数据模型）、[`contracts/public-api.md`](../docs/features/brainstorm/contracts/public-api.md) 与 [`contracts/cli.md`](../docs/features/brainstorm/contracts/cli.md)（接口契约）。本文件只讲**怎么用**，不重复它们的正文。

## 安装

依赖 [weave](https://github.com/) 框架（`13_weave`，`pip install -e .`，核心仅依赖 PyYAML）与 PyYAML：

```bash
pip install -e ../13_weave     # weave 0.1.0（唯一外部框架依赖）
pip install -e .               # brainstorm
```

测试 / 静态检查：

```bash
python -m pytest -q            # 单测 + 集成 + 契约 + e2e + NFR
ruff check brainstorm tests    # lint
mypy brainstorm                # 类型检查
```

## 快速开始（CLI）

默认离线运行（`FakeLLM`，无需 API Key）。`create` 输出的 `session_id` 是后续命令的输入。

```bash
# 1. 创建会话（--config 与 --topic/--personas 二选一）
brainstorm create --topic "如何提升留存" --personas personas.yaml \
    --scheduler round_robin --stop-condition fixed_rounds --max-speeches 6

# 2. 运行到停止条件成立（已存在未跑完则自动恢复）
brainstorm run <session-id>

# 3. 手动停止（配置 manual 停止条件时）
brainstorm stop <session-id>

# 4. 导出讨论记录
brainstorm export <session-id>             # 文本：`seq. speaker: text`
brainstorm export <session-id> --format json   # JSON：Speech[]
```

退出码：`0` 成功；`1` 领域拒绝（消息带错误 `code`，如 `session.topic_required`）；`2` CLI 用法错误（未知命令 / 缺参数 / `--config` 与单项 flag 同时给出）。

## 声明式配置（YAML）

```yaml
topic: "如何提升留存"
personas:
  - {persona_id: "product", name: "产品视角", role_description: "关注用户价值与留存漏斗"}
  - {persona_id: "tech",    name: "技术视角", role_description: "关注实现可行性与稳定性"}
scheduler: round_robin          # round_robin | moderator
stop_condition:
  type: fixed_rounds            # fixed_rounds | convergence | manual
  max_speeches: 6               # 固定轮数 / 收敛兜底上限（>0 生效）
```

```bash
brainstorm create --config config.yaml
```

改这份 YAML 即可改动话题 / 人设 / 策略 / 停止条件，**无需改代码**。

## 四个扩展点

内核只认识四个接口（`contracts/public-api.md` §4），默认实现都在装配时注册；新角色 / 策略 / 停止条件 / 界面经同一注册点接入，**0 处内核改动**。

```python
from brainstorm import Role, Scheduler, StopCondition, Consumer, Registry

class Role(Protocol):
    async def speak(self, ctx: RoleContext) -> str            # 返回发言文本

class Scheduler(Protocol):
    async def next_speaker(self, ctx: SchedulerContext) -> SchedulingDecision  # 选人 or 收敛

class StopCondition(Protocol):
    def evaluate(self, ctx: StopConditionContext) -> StopDecision  # Stop | Continue

class Consumer(Protocol):
    def on_event(self, event: ProgressEvent) -> None          # 订阅进度事件（仅观测）
```

装配默认实现（`brainstorm.wiring.assemble_defaults` 已注册 `round_robin` / `fixed_rounds` / `manual`）：

```python
from brainstorm import Registry, create_session, run_session
from brainstorm.wiring import assemble_defaults

registry = Registry()
assemble_defaults(registry)
registry.register_scheduler("my_strategy", MyScheduler())          # 经扩展点接入
registry.register_stop_condition("my_stop", MyStop())
registry.register_role("product", PersonaRole(...))                # 每会话每人设一个
registry.register_consumer(MyConsumer())                            # 观测进度事件
```

## 引擎 API（library-sdk）

```python
import asyncio
from brainstorm import (
    Repository, Registry, create_session, run_session, stop_session,
    resume_session, read_table, SessionConfig, PersonaConfig, StopConditionConfig,
)
from brainstorm.wiring import assemble_defaults

async def main():
    repository = Repository("./brainstorm.db")
    registry = Registry()
    assemble_defaults(registry)
    # …注册角色（每 persona 一个 PersonaRole）…
    session = await create_session(repository, SessionConfig(
        topic="如何提升留存",
        personas=[PersonaConfig("product", "产品视角", "…"), PersonaConfig("tech", "技术视角", "…")],
        stop_condition=StopConditionConfig(type="fixed_rounds", max_speeches=6),
    ))
    outcome = await run_session(repository, registry, session.session_id)
    print(outcome.speeches)

asyncio.run(main())
```

会话持久化到单个 SQLite 库，按 `brainstorm:{session_id}:*` namespace 隔离；崩溃后可 `resume_session` 恢复到中断那一轮，已落桌发言不重放。
