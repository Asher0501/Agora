"""手动停止（stop_run，AC-11）。"""
from __future__ import annotations

import asyncio

import pytest

from agora.adapter.llm import FakeLLM
from agora.adapter.repository import Repository
from agora.relay import relay
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


# ── AC-11 — 停止标志不被覆盖（运行中的 relay 可观察到停止）──────────────

@pytest.mark.asyncio
async def test_stop_run_preserves_stop_requested_flag(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    await stop_run(repo, _Registry(), run.run_id)
    status = await repo.load_status(run.run_id)
    assert status.get("status") == "stopped"
    assert status.get("stop_requested") is True  # 运行中 relay 轮询的标志不被抹掉


class _GatedLLM:
    """产出在途时挂起，直到显式放行——用于构造「并发停止」的窗口。"""

    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def complete(self, prompt: str) -> str:
        self.started.set()
        await self.release.wait()
        return "在途发言"


@pytest.mark.asyncio
async def test_stop_cancels_inflight_speech_does_not_land(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    llm = _GatedLLM()
    registry = _Registry()
    registry.llm = llm
    task = asyncio.create_task(relay(repo, registry, run.run_id))
    await llm.started.wait()  # 产出在途
    await stop_run(repo, registry, run.run_id)  # 并发停止
    llm.release.set()  # 放行在途生成
    outcome = await asyncio.wait_for(task, timeout=5)
    assert outcome.recap.termination == "manual"
    assert outcome.transcript == []  # 在途发言被取消、不落桌
