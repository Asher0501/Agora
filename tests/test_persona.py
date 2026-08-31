"""T4 — PersonaRole + FakeLLM (AC-04 generation side)."""

import pytest

from brainstorm.business.protocols import RoleContext
from brainstorm.business.types import Speech
from brainstorm.weave_adapter.persona_agent import (
    FakeLLM,
    PersonaPrivateMemory,
    PersonaRole,
)
from brainstorm.weave_adapter.repository import Repository


def _history(n: int) -> list[Speech]:
    return [Speech(seq=i, speaker_id=f"p{i}", text=f"发言{i}") for i in range(1, n + 1)]


@pytest.mark.asyncio
async def test_speak_references_topic_and_history():
    role = PersonaRole("alice", "Alice", "产品视角", FakeLLM(), window_size=20)
    ctx = RoleContext(topic="如何提升留存", history=_history(1), private_memory=None)
    text = await role.speak(ctx)
    assert "如何提升留存" in text  # 针对主题
    assert "p1" in text  # 承接历史发言


@pytest.mark.asyncio
async def test_history_truncated_to_window():
    role = PersonaRole("alice", "Alice", "产品视角", FakeLLM(), window_size=2)
    ctx = RoleContext(topic="主题", history=_history(5), private_memory=None)
    text = await role.speak(ctx)
    assert "2 条历史" in text  # 只注入最近 2 条
    assert "p5" in text  # 最近的发言者在场
    assert "p1" not in text  # 早期历史被截断


@pytest.mark.asyncio
async def test_private_memory_handle_is_persona_scoped(tmp_path):
    repo = Repository(tmp_path / "m.db")
    try:
        mem = PersonaPrivateMemory(repo, "s1", "alice")
        await mem.write("draft", "我的草稿")
        assert await mem.read("draft") == "我的草稿"
        # 同一会话其他人设不可见
        other = PersonaPrivateMemory(repo, "s1", "bob")
        assert await other.read("draft") is None
    finally:
        repo.close()
