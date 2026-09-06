"""集成：并发（≥5 会话）、崩溃恢复（0 丢失/重复）、AC-01 零代码扩展实证。"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from agora.adapter.repository import Repository
from agora.config.schema import load_config
from agora.relay import relay
from agora.session import create_run, resume_run
from agora.types import RoleConfig, RuntimeValues, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


class _Registry:
    def __init__(self, llm):
        self.llm = llm
        self.capabilities = {}
        self.observers = []


class _TopicLLM:
    """按 prompt 里的主题回显（证明无串扰）。"""

    async def complete(self, prompt: str) -> str:
        m = re.search(r"主题：([^\n]+)", prompt)
        topic = m.group(1) if m else "?"
        return f"[{topic}] 发言"


def _scenario(max_rounds=6):
    return ScenarioConfig(
        scenario="brainstorm",
        roles=[
            RoleConfig(id="a", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text"),
            RoleConfig(id="b", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text"),
        ],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="fixed_rounds", max=max_rounds),
    )


@pytest.mark.asyncio
async def test_five_concurrent_runs_no_crosstalk(repo):
    topics = [f"主题{i}" for i in range(5)]
    runs = []
    for t in topics:
        run = await create_run(repo, _scenario(), RuntimeValues(topic=t))
        runs.append(run)

    outcomes = await asyncio.gather(*(relay(repo, _Registry(_TopicLLM()), r.run_id) for r in runs))

    for outcome in outcomes:
        assert len(outcome.transcript) == 6
    for run, topic in zip(runs, topics):
        table = await repo.read_transcript(run.run_id)
        assert all(topic in t.text for t in table)  # 本 run 发言都提到自己的主题
        for other in topics:
            if other != topic:
                assert all(other not in t.text for t in table)  # 无串扰


@pytest.mark.asyncio
async def test_crash_resume_no_replay_no_loss(repo):
    run = await create_run(repo, _scenario(max_rounds=10), RuntimeValues(topic="主题"))
    # 模拟崩溃：落盘 3 条发言后中断
    for i in range(3):
        await repo.append_turn(run.run_id, "a" if i % 2 == 0 else "b", f"崩溃前发言{i}")

    resumed = await resume_run(repo, run.run_id)
    assert resumed.current_seq == 3  # 已落桌 3 条

    outcome = await relay(repo, _Registry(_TopicLLM()), run.run_id)
    assert [t.seq for t in outcome.transcript] == list(range(1, 11))
    assert len(outcome.transcript) == 10  # 不重放、不丢失、不重复


@pytest.mark.asyncio
async def test_consecutive_append_zero_loss_zero_dup(repo):
    run = await create_run(repo, _scenario(max_rounds=200), RuntimeValues(topic="主题"))
    for i in range(200):
        await repo.append_turn(run.run_id, "a" if i % 2 == 0 else "b", f"发言{i}")
    seqs = [t.seq for t in await repo.read_transcript(run.run_id)]
    assert seqs == list(range(1, 201))
    assert len(seqs) == len(set(seqs)) == 200


# ── AC-01 实证：brainstorm 场景 = 纯配置，零引擎代码改动 ────────────────

def test_brainstorm_scenario_runs_via_pure_config(repo):
    path = Path(__file__).resolve().parent.parent / "scenarios" / "brainstorm.yaml"
    scenario = load_config(path)

    async def _run():
        run = await create_run(repo, scenario, RuntimeValues(topic="如何提升留存"))
        outcome = await relay(repo, _Registry(_TopicLLM()), run.run_id)
        return outcome

    outcome = asyncio.run(_run())
    assert outcome.recap.termination == "fixed_rounds"
    assert len(outcome.transcript) == 12  # brainstorm.yaml stop.max = 12
    assert {t.agent_id for t in outcome.transcript} == {"skeptic", "optimizer", "devil"}
