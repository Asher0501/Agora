"""T12 — integration: concurrency (≥5 sessions), durability (crash/resume), 0 loss/dup."""

import asyncio

import pytest

from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.loop import run_session
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session, resume_session
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.weave_adapter.persona_agent import FakeLLM, PersonaRole
from brainstorm.weave_adapter.repository import Repository


def _config(topic="主题", max_speeches=6):
    return SessionConfig(
        topic=topic,
        personas=[
            PersonaConfig(persona_id="a", name="A", role_description="产品"),
            PersonaConfig(persona_id="b", name="B", role_description="技术"),
        ],
        scheduler="round_robin",
        stop_condition=StopConditionConfig(type="fixed_rounds", max_speeches=max_speeches),
    )


def _registry(config):
    registry = Registry()
    for p in config.personas:
        registry.register_role(
            p.persona_id,
            PersonaRole(p.persona_id, p.name, p.role_description, FakeLLM(), 20),
        )
    registry.register_scheduler("round_robin", RoundRobinScheduler())
    registry.register_stop_condition("fixed_rounds", FixedRoundsStop())
    return registry


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


@pytest.mark.asyncio
async def test_five_concurrent_sessions_no_crosstalk(repo):
    topics = [f"主题{i}" for i in range(5)]
    registry = _registry(_config())
    sessions = [await create_session(repo, _config(topic=t)) for t in topics]

    outcomes = await asyncio.gather(
        *(run_session(repo, registry, s.session_id) for s in sessions)
    )

    for outcome in outcomes:
        assert len(outcome.speeches) == 6
    for s, topic in zip(sessions, topics):
        table = await repo.read_table(s.session_id)
        assert len(table) == 6
        # 本会话发言都提到自己的主题，且不含其它会话的主题（无串扰）
        assert all(topic in sp.text for sp in table)
        for other in topics:
            if other != topic:
                assert all(other not in sp.text for sp in table)


@pytest.mark.asyncio
async def test_crash_resume_no_replay_no_loss(repo):
    config = _config(max_speeches=10)
    registry = _registry(config)
    session = await create_session(repo, config)

    # 模拟崩溃：落盘 3 条发言后进程中断（未跑完）
    for i in range(3):
        await repo.append_speech(session.session_id, "a" if i % 2 == 0 else "b", f"崩溃前发言{i}")

    resumed = await resume_session(repo, session.session_id)
    assert resumed.current_seq == 3

    # 恢复后继续跑到 10 条：已落桌 3 条不重放、不丢失、不重复
    outcome = await run_session(repo, registry, session.session_id)
    assert [sp.seq for sp in outcome.speeches] == list(range(1, 11))
    assert len(outcome.speeches) == 10


@pytest.mark.asyncio
async def test_consecutive_append_zero_loss_zero_dup(repo):
    session = await create_session(repo, _config(max_speeches=200))
    for i in range(200):
        await repo.append_speech(session.session_id, "a" if i % 2 == 0 else "b", f"发言{i}")
    table = await repo.read_table(session.session_id)
    seqs = [sp.seq for sp in table]
    assert seqs == list(range(1, 201))
    assert len(seqs) == len(set(seqs)) == 200
