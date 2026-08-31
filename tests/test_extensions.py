"""T5 — default extensions (round_robin scheduler, fixed_rounds / manual stop)."""

import pytest

from brainstorm.business.protocols import SchedulerContext, StopConditionContext
from brainstorm.business.types import PersonaConfig
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.extensions.stop_conditions.manual import ManualStop


def _personas() -> list[PersonaConfig]:
    return [
        PersonaConfig(persona_id="a", role_description="x"),
        PersonaConfig(persona_id="b", role_description="x"),
        PersonaConfig(persona_id="c", role_description="x"),
    ]


def _sched_ctx(last_speaker_id):
    return SchedulerContext(
        session_id="s",
        topic="主题",
        personas=_personas(),
        last_speaker_id=last_speaker_id,
        current_seq=0,
        history=[],
    )


@pytest.mark.asyncio
async def test_round_robin_cycles_in_fixed_order():
    sched = RoundRobinScheduler()
    assert (await sched.next_speaker(_sched_ctx(None))).speaker_id == "a"
    assert (await sched.next_speaker(_sched_ctx("a"))).speaker_id == "b"
    assert (await sched.next_speaker(_sched_ctx("b"))).speaker_id == "c"
    assert (await sched.next_speaker(_sched_ctx("c"))).speaker_id == "a"  # wrap


def test_fixed_rounds_stops_at_max_speeches():
    cond = FixedRoundsStop()
    assert cond.evaluate(
        StopConditionContext(session_id="s", current_seq=2, max_speeches=3)
    ).stop is False
    assert cond.evaluate(
        StopConditionContext(session_id="s", current_seq=3, max_speeches=3)
    ).stop is True


def test_manual_continues_until_stop_requested():
    cond = ManualStop()
    assert cond.evaluate(
        StopConditionContext(session_id="s", current_seq=0, max_speeches=None)
    ).stop is False
    assert cond.evaluate(
        StopConditionContext(
            session_id="s", current_seq=0, max_speeches=None, stop_requested=True
        )
    ).stop is True
