"""T3 — SQLite Repository 适配（weave_agent_sdk memory_entries，AC-16/17 隔离）。"""
from __future__ import annotations

import pytest

from agora.adapter.repository import Repository


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "memory.db")
    yield r
    r.close()


# ── run 状态 roundtrip（config 快照 + status/verdict/recap）──────────────

@pytest.mark.asyncio
async def test_config_snapshot_roundtrip(repo):
    snapshot = {"scenario": {"name": "brainstorm"}, "runtime": {"topic": "主题"}}
    await repo.save_config("r1", snapshot)
    assert await repo.load_config("r1") == snapshot


@pytest.mark.asyncio
async def test_status_verdict_recap_roundtrip(repo):
    await repo.save_status("r1", {"status": "running", "current_seq": 0})
    assert await repo.load_status("r1") == {"status": "running", "current_seq": 0}

    await repo.save_verdict("r1", {"converged": True, "conclusion": "结论"})
    assert await repo.load_verdict("r1") == {"converged": True, "conclusion": "结论"}

    await repo.save_recap("r1", {"termination": "converged", "recap": "总结"})
    assert await repo.load_recap("r1") == {"termination": "converged", "recap": "总结"}


# ── 转录追加 + 按 seq 有序读 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_append_turn_reads_ordered(repo):
    await repo.append_turn("r1", "alice", "第一条")
    await repo.append_turn("r1", "bob", "第二条")
    await repo.append_turn("r1", "alice", "第三条")
    table = await repo.read_transcript("r1")
    assert [t.seq for t in table] == [1, 2, 3]
    assert [t.agent_id for t in table] == ["alice", "bob", "alice"]
    assert [t.text for t in table] == ["第一条", "第二条", "第三条"]


@pytest.mark.asyncio
async def test_consecutive_append_no_loss_no_dup(repo):
    for i in range(50):
        await repo.append_turn("r1", f"p{i % 3}", f"发言 {i}")
    seqs = [t.seq for t in await repo.read_transcript("r1")]
    assert seqs == list(range(1, 51))
    assert len(seqs) == len(set(seqs)) == 50


# ── 跨会话/角色隔离 — AC-16/17 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_namespace_isolation(repo):
    await repo.append_turn("A", "alice", "A 的发言")
    assert await repo.read_transcript("B") == []
    await repo.append_turn("B", "bob", "B 的发言")
    assert [t.text for t in await repo.read_transcript("A")] == ["A 的发言"]
    assert [t.text for t in await repo.read_transcript("B")] == ["B 的发言"]


@pytest.mark.asyncio
async def test_private_state_is_agent_scoped(repo):
    await repo.write_private("r1", "alice", "draft", "alice 的秘密")
    assert await repo.read_private("r1", "alice", "draft") == "alice 的秘密"
    # 同一 run 的其他角色看不到
    assert await repo.read_private("r1", "bob", "draft") is None
    # 跨 run 看不到
    assert await repo.read_private("r2", "alice", "draft") is None


# ── 系统事件与转录分道 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_events_stay_off_the_transcript(repo):
    await repo.append_event("r1", {"type": "invalid_choice", "agent_id": "alice"})
    assert await repo.read_transcript("r1") == []
    events = await repo.read_events("r1")
    assert events[0]["type"] == "invalid_choice"
