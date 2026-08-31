"""T9 — moderator scheduler + convergence stop condition (AC-07/07b/08/10/10b)."""

import pytest

from brainstorm.business.protocols import SchedulerContext, StopConditionContext
from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.loop import run_session
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session
from brainstorm.extensions.schedulers.moderator import ModeratorScheduler
from brainstorm.extensions.stop_conditions.convergence import ConvergenceStop
from brainstorm.weave_adapter.persona_agent import FakeLLM, PersonaRole
from brainstorm.weave_adapter.repository import Repository


class StubRouter:
    """A deterministic router that replays a scripted sequence of decisions."""

    def __init__(self, decisions):
        self.decisions = decisions
        self.i = 0

    async def speak(self, ctx):
        d = self.decisions[self.i % len(self.decisions)]
        self.i += 1
        return d


def _personas():
    return [
        PersonaConfig(persona_id="a", role_description="产品"),
        PersonaConfig(persona_id="b", role_description="技术"),
    ]


def _sched_ctx(last_speaker_id="a"):
    return SchedulerContext(
        session_id="s",
        topic="主题",
        personas=_personas(),
        last_speaker_id=last_speaker_id,
        current_seq=1,
        history=[],
    )


# ── ModeratorScheduler.next_speaker ───────────────────────────────

@pytest.mark.asyncio
async def test_moderator_picks_valid_speaker():
    mod = ModeratorScheduler(StubRouter(["NEXT: b"]))
    decision = await mod.next_speaker(_sched_ctx())
    assert decision.speaker_id == "b"
    assert decision.converged is False


@pytest.mark.asyncio
async def test_moderator_invalid_choice_falls_back():
    mod = ModeratorScheduler(StubRouter(["NEXT: zzz"]))
    decision = await mod.next_speaker(_sched_ctx())  # last=a → fallback b
    assert decision.invalid_choice == "zzz"
    assert decision.speaker_id == "b"


@pytest.mark.asyncio
async def test_moderator_converges_with_conclusion():
    mod = ModeratorScheduler(StubRouter(["CONVERGE: 结论是X"]))
    decision = await mod.next_speaker(_sched_ctx())
    assert decision.converged is True
    assert decision.conclusion == "结论是X"


# ── ConvergenceStop.evaluate ─────────────────────────────────────

def test_convergence_stop_cap_and_converged():
    cond = ConvergenceStop()
    # 未收敛且未达上限 → 继续
    assert cond.evaluate(
        StopConditionContext(session_id="s", current_seq=3, max_speeches=4)
    ).stop is False
    # 达上限仍未收敛 → 强制结束（未收敛，AC-10b）
    cap = cond.evaluate(StopConditionContext(session_id="s", current_seq=4, max_speeches=4))
    assert cap.stop is True
    assert cap.converged is False
    # 已收敛 → 结束并附结论（AC-08/AC-10）
    done = cond.evaluate(
        StopConditionContext(
            session_id="s", current_seq=2, max_speeches=10, converged=True, conclusion="结论"
        )
    )
    assert done.stop is True
    assert done.converged is True
    assert done.conclusion == "结论"


# ── full loop through the moderator ───────────────────────────────

def _config(stop_type="convergence", max_speeches=10):
    return SessionConfig(
        topic="主题",
        personas=_personas(),
        scheduler="moderator",
        stop_condition=StopConditionConfig(type=stop_type, max_speeches=max_speeches),
    )


def _registry(router):
    registry = Registry()
    registry.register_role("a", PersonaRole("a", "A", "产品", FakeLLM(), 20))
    registry.register_role("b", PersonaRole("b", "B", "技术", FakeLLM(), 20))
    registry.register_scheduler("moderator", ModeratorScheduler(router))
    registry.register_stop_condition("convergence", ConvergenceStop())
    return registry


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


@pytest.mark.asyncio
async def test_convergence_happy_path(repo):
    config = _config()
    registry = _registry(StubRouter(["NEXT: a", "NEXT: b", "CONVERGE: 结论是X"]))
    session = await create_session(repo, config)

    outcome = await run_session(repo, registry, session.session_id)

    assert outcome.converged is True
    assert outcome.conclusion == "结论是X"
    assert [s.speaker_id for s in outcome.speeches] == ["a", "b"]


@pytest.mark.asyncio
async def test_convergence_cap_force_stop_not_converged(repo):
    config = _config(max_speeches=3)
    registry = _registry(StubRouter(["NEXT: a", "NEXT: b", "NEXT: a", "NEXT: b"]))
    session = await create_session(repo, config)

    outcome = await run_session(repo, registry, session.session_id)

    assert outcome.converged is False
    assert len(outcome.speeches) == 3
