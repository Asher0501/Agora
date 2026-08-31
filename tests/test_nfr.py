"""T12 — NFR: per-turn orchestration + table-read latency (spec §6)."""

import statistics
import time

import pytest

from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.loop import run_session
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.weave_adapter.persona_agent import FakeLLM, PersonaRole
from brainstorm.weave_adapter.repository import Repository


class TimingConsumer:
    def __init__(self):
        self.landed_at = []

    def on_event(self, event):
        if event.name == "session.speech_landed":
            self.landed_at.append(time.perf_counter())


def _config(max_speeches):
    return SessionConfig(
        topic="主题",
        personas=[
            PersonaConfig(persona_id="a", name="A", role_description="产品"),
            PersonaConfig(persona_id="b", name="B", role_description="技术"),
        ],
        scheduler="round_robin",
        stop_condition=StopConditionConfig(type="fixed_rounds", max_speeches=max_speeches),
    )


def _registry(config, consumer=None):
    registry = Registry()
    for p in config.personas:
        registry.register_role(
            p.persona_id,
            PersonaRole(p.persona_id, p.name, p.role_description, FakeLLM(), 20),
        )
    registry.register_scheduler("round_robin", RoundRobinScheduler())
    registry.register_stop_condition("fixed_rounds", FixedRoundsStop())
    if consumer is not None:
        registry.register_consumer(consumer)
    return registry


def _p95(values):
    if len(values) < 20:
        return max(values, default=0.0)
    return statistics.quantiles(values, n=20)[18]


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


@pytest.mark.asyncio
async def test_turn_overhead_p95(repo):
    config = _config(max_speeches=100)
    consumer = TimingConsumer()
    registry = _registry(config, consumer)
    session = await create_session(repo, config)

    await run_session(repo, registry, session.session_id)

    deltas = [b - a for a, b in zip(consumer.landed_at, consumer.landed_at[1:])]
    assert _p95(deltas) * 1000 <= 100  # p95 ≤ 100 ms


@pytest.mark.asyncio
async def test_table_read_p95(repo):
    config = _config(max_speeches=1000)
    session = await create_session(repo, config)
    for i in range(1000):
        await repo.append_speech(session.session_id, "a", f"发言{i}")

    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        await repo.read_table(session.session_id)
        latencies.append(time.perf_counter() - t0)

    assert _p95(latencies) * 1000 <= 50  # p95 ≤ 50 ms
