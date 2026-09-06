"""T8 — 会话生命周期（create/resume/stop/read，AC-02/02b/11/15/15b）。"""
from __future__ import annotations

import pytest

from agora.adapter.repository import Repository
from agora.errors import (
    RUN_CORRUPTED,
    RUN_NOT_FOUND,
    RUNTIME_VALUE_REQUIRED,
    SCENARIO_NOT_FOUND,
    DomainError,
)
from agora.session import create_run, read_transcript, resume_run, stop_run
from agora.types import RoleConfig, RuntimeValues, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "memory.db")
    yield r
    r.close()


class _Registry:
    def __init__(self):
        self.observers = []


def _scenario(name="brainstorm"):
    return ScenarioConfig(
        scenario=name,
        roles=[RoleConfig(id="alice", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text")],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="fixed_rounds", max=3),
    )


# ── AC-02 / AC-02b ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_run_persists_snapshot(repo):
    run = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    assert run.run_id
    assert run.status == "running"
    assert run.current_seq == 0
    assert await repo.load_config(run.run_id) is not None


@pytest.mark.asyncio
async def test_create_run_rejects_missing_topic(repo):
    with pytest.raises(DomainError) as exc:
        await create_run(repo, _scenario(), RuntimeValues(topic=""))
    assert exc.value.code == RUNTIME_VALUE_REQUIRED


@pytest.mark.asyncio
async def test_create_run_rejects_missing_scenario(repo):
    with pytest.raises(DomainError) as exc:
        await create_run(repo, _scenario(name=""), RuntimeValues(topic="主题"))
    assert exc.value.code == SCENARIO_NOT_FOUND


# ── AC-15 / AC-15b ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_run_reconstructs_from_snapshot(repo):
    created = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    resumed = await resume_run(repo, created.run_id)
    assert resumed.run_id == created.run_id
    assert resumed.scenario.scenario == "brainstorm"
    assert resumed.runtime.topic == "主题"


@pytest.mark.asyncio
async def test_resume_missing_run_raises_not_found(repo):
    with pytest.raises(DomainError) as exc:
        await resume_run(repo, "nonexistent")
    assert exc.value.code == RUN_NOT_FOUND


@pytest.mark.asyncio
async def test_resume_corrupted_run_raises(repo):
    await repo.save_config("r1", {"scenario": "garbage"})  # 非 dict 快照
    with pytest.raises(DomainError) as exc:
        await resume_run(repo, "r1")
    assert exc.value.code == RUN_CORRUPTED


# ── AC-11 — 手动停止 ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stop_run_writes_manual_recap(repo):
    created = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    await repo.append_turn(created.run_id, "alice", "第一条")
    outcome = await stop_run(repo, _Registry(), created.run_id)
    assert outcome.recap.termination == "manual"
    assert outcome.verdict is None
    assert len(outcome.transcript) == 1  # 在途发言不落桌，已落桌保留


# ── read_transcript ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_read_transcript_ordered_and_isolated(repo):
    a = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    b = await create_run(repo, _scenario(), RuntimeValues(topic="主题"))
    await repo.append_turn(a.run_id, "alice", "第一条")
    await repo.append_turn(a.run_id, "bob", "第二条")
    assert [t.seq for t in await read_transcript(repo, a.run_id)] == [1, 2]
    assert await read_transcript(repo, b.run_id) == []  # 越界读不可见（AC-16/17）
