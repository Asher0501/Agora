"""产出侧（render 注入 + FakeLLM 离线 + 私有状态隔离）。"""
from __future__ import annotations

import pytest

from agora.adapter.llm import FakeLLM
from agora.adapter.repository import Repository
from agora.atoms import render
from agora.types import Turn


def _history(n: int) -> list[Turn]:
    return [Turn(run_id="r", seq=i, agent_id=f"p{i}", text=f"发言{i}") for i in range(1, n + 1)]


def test_render_injects_topic_and_history():
    out = render("主题：{topic}\n历史：{history}", {"topic": "如何提升留存", "history": _history(1)}, 20)
    assert "如何提升留存" in out
    assert "p1" in out


def test_render_truncates_history_to_window():
    out = render("{history}", {"history": _history(5)}, 2)
    assert "p5" in out
    assert "p1" not in out


@pytest.mark.asyncio
async def test_fake_llm_is_offline_deterministic():
    fake = FakeLLM()
    assert await fake.complete("任意") == "离线回复"
    assert await fake.complete("任意") == await fake.complete("任意")


@pytest.mark.asyncio
async def test_private_memory_agent_scoped(tmp_path):
    repo = Repository(tmp_path / "m.db")
    try:
        await repo.write_private("s1", "alice", "draft", "我的草稿")
        assert await repo.read_private("s1", "alice", "draft") == "我的草稿"
        assert await repo.read_private("s1", "bob", "draft") is None
    finally:
        repo.close()
