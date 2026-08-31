"""T3 — memory repository (session state / shared table / private memory / events)."""

import pytest

from brainstorm.weave_adapter.repository import Repository


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "memory.db")
    yield r
    r.close()


@pytest.mark.asyncio
async def test_session_state_roundtrip(repo):
    await repo.save_session_config(
        "s1", {"topic": "主题", "personas": [{"persona_id": "alice"}]}
    )
    assert await repo.load_session_config("s1") == {
        "topic": "主题",
        "personas": [{"persona_id": "alice"}],
    }

    await repo.update_session_status("s1", {"status": "running", "current_seq": 0})
    assert await repo.load_session_status("s1") == {"status": "running", "current_seq": 0}

    await repo.write_conclusion("s1", {"converged": True, "conclusion": "结论"})
    assert await repo.load_conclusion("s1") == {"converged": True, "conclusion": "结论"}


@pytest.mark.asyncio
async def test_append_speech_reads_ordered(repo):
    await repo.append_speech("s1", "alice", "第一条")
    await repo.append_speech("s1", "bob", "第二条")
    await repo.append_speech("s1", "alice", "第三条")
    table = await repo.read_table("s1")
    assert [s.seq for s in table] == [1, 2, 3]
    assert [s.speaker_id for s in table] == ["alice", "bob", "alice"]
    assert [s.text for s in table] == ["第一条", "第二条", "第三条"]


@pytest.mark.asyncio
async def test_session_namespace_isolation(repo):
    await repo.append_speech("A", "alice", "A 的发言")
    assert await repo.read_table("B") == []
    await repo.append_speech("B", "bob", "B 的发言")
    assert [s.text for s in await repo.read_table("A")] == ["A 的发言"]
    assert [s.text for s in await repo.read_table("B")] == ["B 的发言"]


@pytest.mark.asyncio
async def test_private_memory_is_persona_scoped(repo):
    await repo.write_private("s1", "alice", "draft", "alice 的秘密")
    assert await repo.read_private("s1", "alice", "draft") == "alice 的秘密"
    # 同一会话的其他人设看不到
    assert await repo.read_private("s1", "bob", "draft") is None
    # 跨会话看不到
    assert await repo.read_private("s2", "alice", "draft") is None


@pytest.mark.asyncio
async def test_consecutive_append_no_loss_no_dup(repo):
    for i in range(50):
        await repo.append_speech("s1", f"p{i % 3}", f"发言 {i}")
    table = await repo.read_table("s1")
    seqs = [s.seq for s in table]
    assert seqs == list(range(1, 51))
    assert len(seqs) == len(set(seqs)) == 50


@pytest.mark.asyncio
async def test_events_stay_off_the_table(repo):
    await repo.append_event("s1", {"type": "skip", "speaker_id": "alice", "reason": "生成失败"})
    assert await repo.read_table("s1") == []
