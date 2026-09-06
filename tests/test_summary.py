"""T9 — 摘要原子与跨轮连续性（AC-12）。"""
from __future__ import annotations

import pytest

from agora.adapter.repository import Repository
from agora.config.schema import scenario_to_dict
from agora.config.validator import validate_config
from agora.errors import INVALID_CONFIG, DomainError
from agora.relay import relay
from agora.types import (
    RoleConfig,
    ScenarioConfig,
    SelectConfig,
    StopConfig,
    SummaryConfig,
)


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "memory.db")
    yield r
    r.close()


class _Registry:
    def __init__(self, llm):
        self.llm = llm
        self.capabilities = {}
        self.observers = []


class _RecordingLLM:
    def __init__(self):
        self.prompts: list[str] = []

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return "发言"


def _scenario():
    return ScenarioConfig(
        scenario="brainstorm",
        roles=[
            RoleConfig(
                id="analyst",
                prompt="你是{name}。主题：{topic}\n摘要：{summary}",
                inject=["topic", "summary"],
                output="free_text",
            )
        ],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="fixed_rounds", max=2),
        summary=SummaryConfig(role="analyst", key="summary", window=20),
    )


@pytest.mark.asyncio
async def test_summary_written_and_injected_across_rounds(repo):
    scenario = _scenario()
    await repo.save_config(
        "r1",
        {"scenario": scenario_to_dict(scenario), "runtime": {"topic": "主题", "stance": None, "extra": {}}},
    )
    await repo.save_status("r1", {"status": "running", "current_seq": 0, "last_agent_id": None})
    llm = _RecordingLLM()
    await relay(repo, _Registry(llm), "r1")

    # 私有状态写入摘要（跨轮连续性）
    assert await repo.read_private("r1", "analyst", "summary") == "analyst: 发言"
    # 第二轮 prompt 注入上一轮发言
    assert "analyst: 发言" in llm.prompts[1]


def test_summary_missing_role_or_key_rejected():
    base = _scenario()
    bad = ScenarioConfig(
        scenario=base.scenario,
        roles=base.roles,
        select=base.select,
        stop=base.stop,
        summary=SummaryConfig(role="", key="summary", window=20),  # role 空
    )
    with pytest.raises(DomainError) as exc:
        validate_config(bad)
    assert exc.value.code == INVALID_CONFIG
