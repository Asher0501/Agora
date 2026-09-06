"""五个原子协议 + 产出/解析 + 闭集菜单原子（零 weave 依赖）。

public-api.md §4 + atomic-relay.md §1：产出（render + LLM + parse）、选人
（selector）、判停（terminator）、存储（StreamStore/StateStore）、摘要
（summarizer）。菜单之外的「新能力 = 新原子 = 写代码」，走扩展区（T6）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .types import Agent, OutputKind, RoleConfig, Termination, Turn

# ── 协议 ────────────────────────────────────────────────────────────────


class LLM(Protocol):
    """唯一能力原子：把 prompt 变成文本。"""

    async def complete(self, prompt: str) -> str: ...


class StreamStore(Protocol):
    """append-only 流（共享转录 / 便签）。"""

    async def append(self, ns: str, entry: dict[str, Any]) -> None: ...
    async def read(self, ns: str) -> list[dict[str, Any]]: ...


class StateStore(Protocol):
    """keyed 状态（run 状态 / agent 私有状态）。"""

    async def get(self, ns: str, key: str) -> Any | None: ...
    async def set(self, ns: str, key: str, value: Any) -> None: ...


class Selector(Protocol):
    """选人原子：决定下一位发言者。"""

    async def next(self, roster: list[Agent], transcript: list[Turn]) -> Selection: ...


class Terminator(Protocol):
    """判停原子：决定是否结束接力（ADR-0007 判停先于产出）。

    注：协议为 ``async``——``llm_verdict`` 需调 judge 的 LLM（public-api §4
    把 ``should_stop`` 写作 sync 是与该原子 async 性的偏差，此处按实现需要
    统一为 async）。
    """

    async def should_stop(self, ctx: dict[str, Any]) -> StopDecision: ...


class Summarizer(Protocol):
    """摘要原子：把共享转录压缩进角色私有状态（US-06 / AC-12）。"""

    async def summarize(self, transcript: list[Turn], ctx: dict[str, Any]) -> str: ...


# ── 产出 / 解析 ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OutputSpec:
    """声明的输出格式。free_text → 原文；pick_next → NEXT:<id>|CONVERGE:<结论>；verdict → CONVERGE:<结论>|CONTINUE。"""

    kind: OutputKind


@dataclass(frozen=True)
class Parsed:
    """LLM 输出的结构化解读。"""

    text: str | None = None
    next_agent_id: str | None = None
    converged: bool = False
    conclusion: str | None = None
    parse_failure: bool = False  # 解析失败（OQ4 → 视为未收敛 + 观测事件）


@dataclass(frozen=True)
class Selection:
    """选人原子的每轮决策。"""

    agent_id: str | None = None
    converged: bool = False
    conclusion: str | None = None
    invalid_choice: str | None = None  # AC-07b：选定的下一位不在名单内


@dataclass(frozen=True)
class StopDecision:
    """判停原子的每轮决策。"""

    stop: bool
    termination: Termination | None = None  # converged | fixed_rounds | cap_unconverged | manual
    converged: bool = False
    conclusion: str | None = None
    parse_failure: bool = False  # llm_verdict 裁判解析失败（OQ4，视为未收敛）


def render(template: str, ctx: dict[str, Any], window: int) -> str:
    """注入上下文字段 + 把 ``ctx["history"]`` 截断到最近 ``window`` 条再替换。

    ``window <= 0`` 表示不截断（全量 history）。history 条目可为 ``Turn``
    （格式化为 ``agent_id: text``）或任意可 ``str()`` 的值。
    """
    c = dict(ctx)
    history = list(c.get("history") or [])
    if window and window > 0:
        history = history[-window:]
    c["history"] = "\n".join(_line(h) for h in history)
    return template.format(**c)


def _line(h: Any) -> str:
    if isinstance(h, Turn):
        return f"{h.agent_id}: {h.text}"
    return str(h)


def parse(text: str, spec: OutputSpec) -> Parsed:
    """按声明格式解读 LLM 输出；解析失败置 ``parse_failure=True``。"""
    s = (text or "").strip()
    if spec.kind == "free_text":
        return Parsed(text=s)
    if spec.kind == "pick_next":
        if s.startswith("CONVERGE:"):
            return Parsed(converged=True, conclusion=_tail(s, "CONVERGE:"))
        if s.startswith("NEXT:"):
            return Parsed(next_agent_id=_tail(s, "NEXT:"))
        return Parsed(parse_failure=True)
    if spec.kind == "verdict":
        if s.startswith("CONVERGE:"):
            return Parsed(converged=True, conclusion=_tail(s, "CONVERGE:"))
        if s == "CONTINUE":
            return Parsed(converged=False)
        return Parsed(parse_failure=True)
    return Parsed(parse_failure=True)


def _tail(text: str, prefix: str) -> str | None:
    return text[len(prefix):].strip() or None


# ── 菜单原子 ────────────────────────────────────────────────────────────


class RoundRobinSelector:
    """round_robin — 按 roster 顺序轮转（正反交替 = 2 人轮转）。纯状态函数。"""

    async def next(self, roster: list[Agent], transcript: list[Turn]) -> Selection:
        ids = [a.agent_id for a in roster]
        if not ids:
            return Selection()
        last = transcript[-1].agent_id if transcript else None
        if last is None or last not in ids:
            return Selection(agent_id=ids[0])
        return Selection(agent_id=ids[(ids.index(last) + 1) % len(ids)])


class LlmPickSelector:
    """llm_pick — 让 picker 角色选下一位（``pick_next`` 输出）。"""

    def __init__(self, llm: LLM, picker: RoleConfig):
        self._llm = llm
        self._picker = picker

    async def next(self, roster: list[Agent], transcript: list[Turn]) -> Selection:
        prompt = render(
            self._picker.prompt,
            {"name": self._picker.id, "history": transcript},
            self._picker.window,
        )
        parsed = parse(await self._llm.complete(prompt), OutputSpec(kind="pick_next"))
        if parsed.converged:
            return Selection(converged=True, conclusion=parsed.conclusion)
        if parsed.next_agent_id is not None:
            roster_ids = [a.agent_id for a in roster]
            if parsed.next_agent_id in roster_ids:
                return Selection(agent_id=parsed.next_agent_id)
            return Selection(invalid_choice=parsed.next_agent_id)
        return Selection()  # 解析失败 → 无选择，交由 relay 回退（AC-07b）


class FixedRoundsTerminator:
    """fixed_rounds — 发言数达 ``max`` 停止。纯状态函数，不调 LLM。"""

    async def should_stop(self, ctx: dict[str, Any]) -> StopDecision:
        max_ = ctx.get("max")
        if max_ is not None and ctx.get("current_seq", 0) >= max_:
            return StopDecision(stop=True, termination="fixed_rounds")
        return StopDecision(stop=False)


class LlmVerdictTerminator:
    """llm_verdict — 让 judge 角色裁决收敛（``verdict`` 输出），``max`` 兜底。"""

    def __init__(self, llm: LLM, judge: RoleConfig):
        self._llm = llm
        self._judge = judge

    async def should_stop(self, ctx: dict[str, Any]) -> StopDecision:
        transcript = ctx.get("transcript", [])
        prompt = render(
            self._judge.prompt,
            {"name": self._judge.id, "history": transcript},
            self._judge.window,
        )
        parsed = parse(await self._llm.complete(prompt), OutputSpec(kind="verdict"))
        if parsed.parse_failure:
            # OQ4：视为未收敛 + 观测事件（由 relay 记录）
            return StopDecision(stop=False, parse_failure=True)
        if parsed.converged:
            return StopDecision(
                stop=True, termination="converged", converged=True, conclusion=parsed.conclusion
            )
        # CONTINUE → 达 max 兜底则 cap_unconverged（AC-10b）
        max_ = ctx.get("max")
        if max_ is not None and ctx.get("current_seq", 0) >= max_:
            return StopDecision(stop=True, termination="cap_unconverged")
        return StopDecision(stop=False)


class ManualTerminator:
    """manual — 收到停止指令停止（进程内停止标志）。"""

    async def should_stop(self, ctx: dict[str, Any]) -> StopDecision:
        if ctx.get("stop_requested"):
            return StopDecision(stop=True, termination="manual")
        return StopDecision(stop=False)


# 闭集菜单锚点（T5 校验 / T6 扩展区的「已知能力」= 菜单 ∪ registry）。
MENU_SELECTORS = frozenset({"round_robin", "llm_pick"})
MENU_TERMINATORS = frozenset({"fixed_rounds", "llm_verdict", "manual"})
MENU = frozenset(MENU_SELECTORS | MENU_TERMINATORS)
