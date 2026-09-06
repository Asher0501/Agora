"""手动停止（stop_run，AC-11）。"""
from __future__ import annotations

import pytest

from agora.adapter.llm import FakeLLM
from agora.adapter.repository import Repository
from agora.session import create_run, stop_run
from agora.types import RoleConfig, RuntimeValues, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


class _Registry:
    def __init__(self):
        self.llm = FakeLLM()
        self.capabilities = {}
        self.observers = []


def _scenario():
    return ScenarioConfig(
        scenario="brainstorm",
        roles=[RoleConfig(id="a", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text")],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="manual"),
    )


@pytest.mark.asyncio
async def test_stop_immediate_without_loop(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    outcome = await stop_run(repo, _Registry(), run.run_id)
    assert outcome.status == "stopped"
    assert outcome.transcript == []
    assert outcome.recap.termination == "manual"


@pytest.mark.asyncio
async def test_stop_retains_landed_record(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    await repo.append_turn(run.run_id, "a", "已落桌发言")
    outcome = await stop_run(repo, _Registry(), run.run_id)
    assert len(outcome.transcript) == 1  # 已落桌保留


class _Recorder:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


@pytest.mark.asyncio
async def test_stop_emits_stopped_event(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    registry = _Registry()
    recorder = _Recorder()
    registry.observers.append(recorder)
    await stop_run(repo, registry, run.run_id)
    assert [e.name for e in recorder.events] == ["run.stopped"]
