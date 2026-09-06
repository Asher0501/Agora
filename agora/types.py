"""中性领域类型（零 weave 依赖）— public-api.md §2 / data-model.md §Entities.

Session/Speech/Persona 已中性化为 Run/Turn/Agent；全部为 frozen dataclass +
Literal 枚举（ADR-0002「命名中性化」）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

RunStatus = Literal["running", "stopped"]
SelectKind = Literal["round_robin", "llm_pick"]
StopKind = Literal["fixed_rounds", "llm_verdict", "manual"]
OutputKind = Literal["free_text", "pick_next", "verdict"]
Termination = Literal["converged", "fixed_rounds", "cap_unconverged", "manual"]


@dataclass(frozen=True)
class RoleConfig:
    """config.scenario.roles[] — 一个角色的定义（data-model §AGENT 物化来源）。"""

    id: str
    prompt: str  # 产出模板；占位符 {name} {role_description} {stance} {topic} {history}
    inject: list[str] = field(default_factory=list)  # 只注入列出的上下文字段
    window: int = 0  # history 截断条数
    output: OutputKind = "free_text"  # free_text | pick_next | verdict


@dataclass(frozen=True)
class SelectConfig:
    """config.scenario.select — 选人方式。"""

    type: SelectKind  # round_robin | llm_pick
    role: str | None = None  # 仅 llm_pick：由哪个角色选人


@dataclass(frozen=True)
class StopConfig:
    """config.scenario.stop — 判停方式。"""

    type: StopKind  # fixed_rounds | llm_verdict | manual
    max: int | None = None  # fixed_rounds 的轮数 / llm_verdict 的兜底上限
    judge: str | None = None  # 仅 llm_verdict：由哪个角色裁决


@dataclass(frozen=True)
class SummaryConfig:
    """config.scenario.summary — 最小形状（role/key/window，data-model §RUN summary 已 ratify）。"""

    role: str  # 为哪个角色摘要
    key: str  # 写入私有 state 的键
    window: int = 20  # 摘要窗口条数


@dataclass(frozen=True)
class ScenarioConfig:
    """场景配置（快照的 scenario 段）。"""

    scenario: str  # 场景名
    roles: list[RoleConfig]
    select: SelectConfig
    stop: StopConfig
    summary: SummaryConfig | None = None


@dataclass(frozen=True)
class RuntimeValues:
    """运行时值（每场会话注入，不写进配置）。"""

    topic: str  # 主题（AC-02b：缺主题拒绝启动）
    stance: str | None = None  # 立场（辩论场景注入）
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Run:
    """聚合根（data-model §RUN）——创建时定格的配置快照 + 共享转录 + 终止产物。"""

    run_id: str
    scenario: ScenarioConfig
    runtime: RuntimeValues
    status: RunStatus = "running"
    current_seq: int = 0  # 下一 turn 的序号，单调递增
    verdict: Verdict | None = None  # 仅裁判收敛路径（AC-08）
    recap: Recap | None = None  # 任意终止路径（AC-08/09/10b/11）
    created_at: float = 0.0


@dataclass(frozen=True)
class Turn:
    """一条发言（data-model §TURN）。"""

    run_id: str
    seq: int  # 显式 run 内单调序号（追加顺序不变量的载体）
    agent_id: str  # 发言者（系统标注，AC-05）
    text: str
    created_at: float = 0.0


@dataclass(frozen=True)
class Agent:
    """一个角色在某个 run 里的实例（data-model §AGENT）。"""

    run_id: str
    agent_id: str
    role_description: str


@dataclass(frozen=True)
class Verdict:
    """裁判收敛判断（data-model §RUN.verdict）。"""

    converged: bool
    conclusion: str | None


@dataclass(frozen=True)
class Recap:
    """全局复盘 + 终止方式标注（data-model §RUN.recap）。"""

    termination: Termination  # converged | fixed_rounds | cap_unconverged | manual
    recap: str


@dataclass(frozen=True)
class RunOutcome:
    """终止产物（US-02）。"""

    run_id: str
    status: RunStatus
    verdict: Verdict | None
    recap: Recap
    transcript: list[Turn]
