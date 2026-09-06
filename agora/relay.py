"""接力循环（ADR-0007）：每轮 选人 → 判停 →（未停才）产出 → 落桌。

引擎的核心编排，无语义（sad §4 内联）：只强制「业务无关」机制——追加顺序
不变量（每 turn 恰好一条）、跨会话隔离、判停先于产出。「自选自判」「选人反复
点中同一角色」等业务行为留给场景作者在 prompt 里约束（spec §8 OQ1）。

进度事件（AC-18）是进程内发布-订阅，只携带本 run 内容，不持久化；落盘的
观测事件（invalid_choice / verdict_parse_failure）经 repository 写独立
namespace（data-model §System records）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .atoms import (
    FixedRoundsTerminator,
    LlmPickSelector,
    LlmVerdictTerminator,
    ManualTerminator,
    OutputSpec,
    RoundRobinSelector,
    WindowSummarizer,
    parse,
    render,
)
from .config.schema import runtime_from_dict, scenario_from_dict
from .errors import INVALID_CONFIG, INVALID_STATE, RUN_NOT_FOUND, UNKNOWN_CAPABILITY, DomainError
from .types import (
    Agent,
    Recap,
    RoleConfig,
    RunOutcome,
    RuntimeValues,
    ScenarioConfig,
    Termination,
    Turn,
    Verdict,
)


@dataclass(frozen=True)
class ProgressEvent:
    """进程内进度事件（AC-18）。"""

    name: str
    run_id: str
    payload: dict[str, Any] = field(default_factory=dict)


class Observer(Protocol):
    def on_event(self, event: ProgressEvent) -> None: ...


async def relay(repository: Any, registry: Any, run_id: str) -> RunOutcome:
    """驱动接力循环直到终止（收敛 / 达条数 / 达上限未收敛 / 手动停止）。"""
    config = await repository.load_config(run_id)
    if config is None:
        raise DomainError(RUN_NOT_FOUND, f"会话 {run_id} 不存在")
    scenario = scenario_from_dict(config["scenario"])
    runtime = runtime_from_dict(config.get("runtime") or {})

    status = await repository.load_status(run_id) or {}
    if status.get("status") == "stopped":
        raise DomainError(INVALID_STATE, f"会话 {run_id} 已结束，无法继续")

    # 发言名单 = free_text 角色；pick_next（选人）/ verdict（裁判）角色不参与接力发言。
    roster = [
        Agent(run_id=run_id, agent_id=r.id, role_description=r.prompt)
        for r in scenario.roles
        if r.output == "free_text"
    ]
    selector = _build_selector(scenario, registry)
    terminator = _build_terminator(scenario, registry)
    transcript: list[Turn] = await repository.read_transcript(run_id)

    def _emit(name: str, payload: dict[str, Any]) -> None:
        for observer in getattr(registry, "observers", []):
            observer.on_event(ProgressEvent(name=name, run_id=run_id, payload=payload))

    termination: Termination | None = None
    converged = False
    conclusion: str | None = None

    while True:
        status = await repository.load_status(run_id) or {}
        if status.get("status") == "stopped":
            termination = "manual"
            break
        stop_requested = bool(status.get("stop_requested"))

        agent_id, sel_converged, sel_conclusion = await _select_agent(
            selector, roster, transcript, repository, run_id
        )
        if sel_converged:
            converged, conclusion, termination = True, sel_conclusion, "converged"
            _emit("run.converged", {"conclusion": conclusion})
            break
        if agent_id is None:
            break  # 空 roster 或回退无果

        decision = await terminator.should_stop(
            {
                "current_seq": len(transcript),
                "max": scenario.stop.max,
                "transcript": transcript,
                "stop_requested": stop_requested,
            }
        )
        if decision.parse_failure:
            await repository.append_event(
                run_id,
                {"type": "verdict_parse_failure", "agent_id": scenario.stop.judge, "reason": "裁判解析失败"},
            )
        if decision.stop:
            termination = decision.termination or "cap_unconverged"
            if decision.converged:
                converged, conclusion = True, decision.conclusion
                _emit("run.converged", {"conclusion": conclusion})
            break

        role = _find_role(scenario.roles, agent_id)
        _emit("run.turn_started", {"seq": len(transcript) + 1, "agent_id": agent_id})
        text = await _produce(role, runtime, transcript, registry.llm, scenario.summary, repository, run_id)
        # AC-11：产出在途期间收到停止 → 取消该发言（不落桌），终止接力。
        status = await repository.load_status(run_id) or {}
        if status.get("stop_requested") or status.get("status") == "stopped":
            termination = "manual"
            break
        turn = await repository.append_turn(run_id, agent_id, text)
        transcript.append(turn)
        _emit("run.turn_landed", {"seq": turn.seq, "agent_id": agent_id})

    return await _finalize(repository, run_id, transcript, termination, converged, conclusion, _emit)


# ── 选人（含 AC-07b 无效重试 + 回退）───────────────────────────────────


async def _select_agent(selector: Any, roster: list[Agent], transcript: list[Turn], repository: Any, run_id: str):
    """返回 (agent_id, converged, conclusion)。无效选择重试 1 次，仍无效回退名单顺序。"""
    selection = await selector.next(roster, transcript)
    if selection.converged:
        return None, True, selection.conclusion
    if selection.invalid_choice:
        await repository.append_event(
            run_id, {"type": "invalid_choice", "agent_id": selection.invalid_choice, "reason": "选定的下一位不在名单内"}
        )
        retry = await selector.next(roster, transcript)
        if retry.converged:
            return None, True, retry.conclusion
        if retry.invalid_choice:
            await repository.append_event(
                run_id, {"type": "invalid_choice", "agent_id": retry.invalid_choice, "reason": "重试后仍无效"}
            )
            return (await RoundRobinSelector().next(roster, transcript)).agent_id, False, None
        selection = retry
    if selection.agent_id is None:
        # 解析失败 / 无选择 → 回退名单顺序
        return (await RoundRobinSelector().next(roster, transcript)).agent_id, False, None
    return selection.agent_id, False, None


def _build_selector(scenario: ScenarioConfig, registry: Any) -> Any:
    t = scenario.select.type
    if t == "round_robin":
        return RoundRobinSelector()
    if t == "llm_pick":
        picker = _find_role(scenario.roles, scenario.select.role)
        return LlmPickSelector(registry.llm, picker)
    cap = getattr(registry, "capabilities", {}).get(t)
    if cap is None:
        raise DomainError(UNKNOWN_CAPABILITY, f"选人方式 {t} 不受支持")
    return cap


def _build_terminator(scenario: ScenarioConfig, registry: Any) -> Any:
    t = scenario.stop.type
    if t == "fixed_rounds":
        return FixedRoundsTerminator()
    if t == "manual":
        return ManualTerminator()
    if t == "llm_verdict":
        judge = _find_role(scenario.roles, scenario.stop.judge)
        return LlmVerdictTerminator(registry.llm, judge)
    cap = getattr(registry, "capabilities", {}).get(t)
    if cap is None:
        raise DomainError(UNKNOWN_CAPABILITY, f"判停方式 {t} 不受支持")
    return cap


async def _produce(
    role: RoleConfig,
    runtime: RuntimeValues,
    transcript: list[Turn],
    llm: Any,
    summary: Any = None,
    repository: Any = None,
    run_id: str | None = None,
) -> str:
    """产出：render（注入字段 + 截断 history）→ llm.complete → parse。

    若该角色配置了 summary（AC-12）：先压缩共享转录 → 写私有 state → 注入 prompt。
    """
    ctx = _build_ctx(role, runtime, transcript)
    if summary is not None and summary.role == role.id:
        summary_text = await WindowSummarizer().summarize(transcript, {"window": summary.window})
        if repository is not None and run_id is not None:
            await repository.write_private(run_id, role.id, summary.key, summary_text)
        ctx[summary.key] = summary_text
    prompt = render(role.prompt, ctx, role.window)
    text = await llm.complete(prompt)
    return parse(text, OutputSpec(kind="free_text")).text or text


def _build_ctx(role: RoleConfig, runtime: RuntimeValues, transcript: list[Turn]) -> dict[str, Any]:
    """构造角色的上下文字段，只注入 inject 声明的字段 + 身份字段。"""
    full = {
        "name": role.id,
        "role_description": role.prompt,  # data-model §AGENT：描述即 prompt
        "topic": runtime.topic,
        "stance": runtime.stance or "",
        "history": transcript,
    }
    inject = set(role.inject) | {"name", "role_description"}
    return {k: v for k, v in full.items() if k in inject}


def _find_role(roles: list[RoleConfig], role_id: str | None) -> RoleConfig:
    for r in roles:
        if r.id == role_id:
            return r
    raise DomainError(INVALID_CONFIG, f"角色 {role_id} 不在名单内")


async def _finalize(
    repository: Any,
    run_id: str,
    transcript: list[Turn],
    termination: Termination | None,
    converged: bool,
    conclusion: str | None,
    emit,
) -> RunOutcome:
    termination = termination or "manual"
    verdict: Verdict | None = None
    if termination == "converged":
        verdict = Verdict(converged=True, conclusion=conclusion)
    recap_text = f"本场接力共 {len(transcript)} 条发言，终止方式：{termination}"
    await repository.save_status(
        run_id,
        {"status": "stopped", "current_seq": len(transcript), "last_agent_id": transcript[-1].agent_id if transcript else None},
    )
    if verdict is not None:
        await repository.save_verdict(run_id, {"converged": verdict.converged, "conclusion": verdict.conclusion})
    await repository.save_recap(run_id, {"termination": termination, "recap": recap_text})
    emit("run.stopped", {"status": "stopped"})
    return RunOutcome(
        run_id=run_id,
        status="stopped",
        verdict=verdict,
        recap=Recap(termination=termination, recap=recap_text),
        transcript=transcript,
    )
