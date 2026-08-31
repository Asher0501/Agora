"""T8 — turn orchestration loop run_session (AC-04/04b/09/14/15, ADR-0004)."""

import pytest

from brainstorm.business.errors import ROUND_QUOTA_EXHAUSTED, DomainError
from brainstorm.business.protocols import SchedulingDecision
from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.loop import run_session
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.extensions.stop_conditions.manual import ManualStop
from brainstorm.weave_adapter.persona_agent import FakeLLM, PersonaRole
from brainstorm.weave_adapter.repository import Repository


def _config(max_speeches=4):
    return SessionConfig(
        topic="如何提升留存",
        personas=[
            PersonaConfig(persona_id="a", name="A", role_description="产品"),
            PersonaConfig(persona_id="b", name="B", role_description="技术"),
        ],
        scheduler="round_robin",
        stop_condition=StopConditionConfig(type="fixed_rounds", max_speeches=max_speeches),
    )


class RecordingConsumer:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


class AlwaysAScheduler:
    async def next_speaker(self, ctx):
        return SchedulingDecision(speaker_id="a")


class FailingLLM:
    async def chat(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        raise RuntimeError("boom")

    async def chat_stream(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        raise RuntimeError("boom")


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


def _register_roles(registry, config, llm=FakeLLM()):
    for p in config.personas:
        registry.register_role(
            p.persona_id, PersonaRole(p.persona_id, p.name, p.role_description, llm, 20)
        )


def _register_defaults(registry):
    registry.register_scheduler("round_robin", RoundRobinScheduler())
    registry.register_stop_condition("fixed_rounds", FixedRoundsStop())
    registry.register_stop_condition("manual", ManualStop())


@pytest.mark.asyncio
async def test_run_fixed_rounds_happy_path(repo):
    config = _config(max_speeches=4)
    registry = Registry()
    _register_roles(registry, config)
    _register_defaults(registry)
    session = await create_session(repo, config)

    outcome = await run_session(repo, registry, session.session_id)

    assert outcome.status == "stopped"
    assert [s.seq for s in outcome.speeches] == [1, 2, 3, 4]
    assert [s.speaker_id for s in outcome.speeches] == ["a", "b", "a", "b"]
    assert outcome.converged is False


@pytest.mark.asyncio
async def test_round_quota_second_append_rejected(repo):
    config = _config(max_speeches=4)
    registry = Registry()
    _register_roles(registry, config)
    registry.register_scheduler("round_robin", AlwaysAScheduler())
    registry.register_stop_condition("fixed_rounds", FixedRoundsStop())
    session = await create_session(repo, config)

    with pytest.raises(DomainError) as exc:
        await run_session(repo, registry, session.session_id)
    assert exc.value.code == ROUND_QUOTA_EXHAUSTED


@pytest.mark.asyncio
async def test_generation_failure_skips_and_continues(repo):
    config = _config(max_speeches=2)
    registry = Registry()
    registry.register_role("a", PersonaRole("a", "A", "产品", FailingLLM(), 20))
    registry.register_role("b", PersonaRole("b", "B", "技术", FakeLLM(), 20))
    _register_defaults(registry)
    session = await create_session(repo, config)

    outcome = await run_session(repo, registry, session.session_id, max_retries=1)

    assert [s.speaker_id for s in outcome.speeches] == ["b", "b"]
    events = await repo.read_events(session.session_id)
    skips = [e for e in events if e.get("type") == "skip"]
    assert len(skips) >= 2  # a 被跳过至少两次


@pytest.mark.asyncio
async def test_progress_events_in_order(repo):
    config = _config(max_speeches=4)
    registry = Registry()
    _register_roles(registry, config)
    _register_defaults(registry)
    consumer = RecordingConsumer()
    registry.register_consumer(consumer)
    session = await create_session(repo, config)

    await run_session(repo, registry, session.session_id)

    assert [e.name for e in consumer.events] == [
        "session.turn_started",
        "session.speech_landed",
        "session.turn_started",
        "session.speech_landed",
        "session.turn_started",
        "session.speech_landed",
        "session.turn_started",
        "session.speech_landed",
        "session.stopped",
    ]
