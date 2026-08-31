"""T10 — manual stop (stop_session) with in-flight safety (AC-11/11b)."""

import asyncio

import pytest
from weave.llm.base import LLMResponse

from brainstorm.business.types import PersonaConfig, SessionConfig, StopConditionConfig
from brainstorm.engine.loop import run_session
from brainstorm.engine.registry import Registry
from brainstorm.engine.session import create_session
from brainstorm.engine.stop import stop_session
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.manual import ManualStop
from brainstorm.weave_adapter.persona_agent import FakeLLM, PersonaRole
from brainstorm.weave_adapter.repository import Repository


class SlowLLM:
    """A slow LLM so a stop can land mid-generation."""

    async def chat(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        await asyncio.sleep(0.1)
        return LLMResponse(content="慢速发言")

    async def chat_stream(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        await asyncio.sleep(0.1)
        yield "慢速发言"


def _config():
    return SessionConfig(
        topic="主题",
        personas=[PersonaConfig("a", "A", "产品"), PersonaConfig("b", "B", "技术")],
        scheduler="round_robin",
        stop_condition=StopConditionConfig(type="manual"),
    )


def _registry(llm=FakeLLM()):
    registry = Registry()
    for pid, name, role in [("a", "A", "产品"), ("b", "B", "技术")]:
        registry.register_role(pid, PersonaRole(pid, name, role, llm, 20))
    registry.register_scheduler("round_robin", RoundRobinScheduler())
    registry.register_stop_condition("manual", ManualStop())
    return registry


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


async def _wait_for_speeches(repo, session_id, n, timeout=2.0):
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(await repo.read_table(session_id)) >= n:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("timeout waiting for speeches")


@pytest.mark.asyncio
async def test_stop_session_immediate_without_loop(repo):
    registry = _registry()
    session = await create_session(repo, _config())

    outcome = await stop_session(repo, registry, session.session_id)

    assert outcome.status == "stopped"
    assert outcome.speeches == []
    assert outcome.converged is False


@pytest.mark.asyncio
async def test_stop_session_ends_and_retains_record(repo):
    registry = _registry(SlowLLM())
    session = await create_session(repo, _config())
    task = asyncio.create_task(run_session(repo, registry, session.session_id))

    await _wait_for_speeches(repo, session.session_id, 3)
    outcome = await stop_session(repo, registry, session.session_id)
    await task

    assert outcome.status == "stopped"
    assert len(outcome.speeches) >= 3


@pytest.mark.asyncio
async def test_stop_waits_for_inflight_speech(repo):
    registry = _registry(SlowLLM())
    session = await create_session(repo, _config())
    task = asyncio.create_task(run_session(repo, registry, session.session_id))

    await asyncio.sleep(0.05)  # 生成在途
    outcome = await stop_session(repo, registry, session.session_id)
    await task

    assert len(outcome.speeches) >= 1  # 在途发言已落桌，未丢失
