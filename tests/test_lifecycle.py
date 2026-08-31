"""T7 — engine lifecycle (create / resume / read_table) + extension registry."""

import pytest

from brainstorm.business.errors import NOT_FOUND, TOPIC_REQUIRED, DomainError
from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session, resume_session
from brainstorm.engine.table import read_table
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.weave_adapter.repository import Repository


def _config(topic="主题"):
    return SessionConfig(
        topic=topic,
        personas=[
            PersonaConfig(persona_id="a", name="A", role_description="产品"),
            PersonaConfig(persona_id="b", name="B", role_description="技术"),
        ],
        scheduler="round_robin",
        stop_condition=StopConditionConfig(type="fixed_rounds", max_speeches=4),
    )


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


@pytest.mark.asyncio
async def test_create_session_persists_and_returns(repo):
    session = await create_session(repo, _config())
    assert session.session_id
    assert session.topic == "主题"
    assert session.status == "running"
    assert session.current_seq == 0
    assert await repo.load_session_config(session.session_id) is not None


@pytest.mark.asyncio
async def test_create_session_rejects_invalid_config(repo):
    with pytest.raises(DomainError) as exc:
        await create_session(repo, _config(topic=""))
    assert exc.value.code == TOPIC_REQUIRED


@pytest.mark.asyncio
async def test_resume_session_reconstructs(repo):
    created = await create_session(repo, _config())
    resumed = await resume_session(repo, created.session_id)
    assert resumed.session_id == created.session_id
    assert resumed.topic == "主题"
    assert [p.persona_id for p in resumed.personas] == ["a", "b"]


@pytest.mark.asyncio
async def test_resume_missing_session_raises_not_found(repo):
    with pytest.raises(DomainError) as exc:
        await resume_session(repo, "nonexistent")
    assert exc.value.code == NOT_FOUND


@pytest.mark.asyncio
async def test_read_table_ordered_and_cross_session_isolated(repo):
    a = await create_session(repo, _config())
    b = await create_session(repo, _config())
    await repo.append_speech(a.session_id, "a", "第一条")
    await repo.append_speech(a.session_id, "b", "第二条")
    assert [s.seq for s in await read_table(repo, a.session_id)] == [1, 2]
    assert await read_table(repo, b.session_id) == []  # 越界读：B 不含 A 的内容


def test_registry_roundtrip():
    reg = Registry()
    sched = RoundRobinScheduler()
    cond = FixedRoundsStop()
    role = object()
    consumer = object()
    reg.register_scheduler("round_robin", sched)
    reg.register_stop_condition("fixed_rounds", cond)
    reg.register_role("a", role)
    reg.register_consumer(consumer)
    assert reg.get_scheduler("round_robin") is sched
    assert reg.get_stop_condition("fixed_rounds") is cond
    assert reg.get_role("a") is role
    assert consumer in reg.consumers
