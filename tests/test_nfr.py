"""T15 — NFR：追加顺序不变量（QG-2）、并发隔离（QG-5）、延迟插桩（QG-4）。"""
from __future__ import annotations

import asyncio
import statistics
import time

import pytest

from agora.adapter.repository import Repository
from agora.relay import relay
from agora.session import create_run
from agora.types import RoleConfig, RuntimeValues, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "m.db")
    yield r
    r.close()


class _Registry:
    def __init__(self, llm, observers=None):
        self.llm = llm
        self.capabilities = {}
        self.observers = observers or []


class _FixedLLM:
    async def complete(self, prompt: str) -> str:
        return "发言"


class _TimingObserver:
    def __init__(self):
        self.landed_at: list[float] = []

    def on_event(self, event) -> None:
        if event.name == "run.turn_landed":
            self.landed_at.append(time.perf_counter())


class _TurnDurationObserver:
    """记录每个 turn 的产出耗时（started → landed），供 QG-5 并发比率测量。"""

    def __init__(self):
        self._started: dict[str, float] = {}
        self.durations: list[float] = []

    def on_event(self, event) -> None:
        if event.name == "run.turn_started":
            self._started[event.run_id] = time.perf_counter()
        elif event.name == "run.turn_landed":
            start = self._started.pop(event.run_id, None)
            if start is not None:
                self.durations.append(time.perf_counter() - start)


def _scenario(max_rounds: int):
    return ScenarioConfig(
        scenario="brainstorm",
        roles=[
            RoleConfig(id="a", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text"),
            RoleConfig(id="b", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text"),
        ],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="fixed_rounds", max=max_rounds),
    )


def _p95(values: list[float]) -> float:
    if len(values) < 20:
        return max(values, default=0.0)
    return statistics.quantiles(values, n=20)[18]


# ── QG-2：追加顺序不变量（0 丢失 / 0 重复）────────────────────────────

@pytest.mark.asyncio
async def test_append_order_invariant_zero_loss_zero_dup(repo):
    run = await create_run(repo, _scenario(max_rounds=100), RuntimeValues(topic="主题"))
    await relay(repo, _Registry(_FixedLLM()), run.run_id)
    seqs = [t.seq for t in await repo.read_transcript(run.run_id)]
    assert seqs == list(range(1, 101))  # 0 丢失
    assert len(seqs) == len(set(seqs)) == 100  # 0 重复


# ── QG-5：≥5 并发会话隔离 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_five_concurrent_runs_isolated(repo):
    runs = [await create_run(repo, _scenario(max_rounds=4), RuntimeValues(topic=f"主题{i}")) for i in range(5)]
    outcomes = await asyncio.gather(*(relay(repo, _Registry(_FixedLLM()), r.run_id) for r in runs))
    assert all(len(o.transcript) == 4 for o in outcomes)
    # 各 run 转录互不可见（AC-16/17）：只含本 run 的发言
    for run in runs:
        turns = await repo.read_transcript(run.run_id)
        assert all(t.run_id == run.run_id for t in turns)


@pytest.mark.asyncio
async def test_concurrent_p95_within_2x_single_baseline(repo):
    # 单会话基线：30 条发言的每轮编排耗时 p95
    single_obs = _TurnDurationObserver()
    run = await create_run(repo, _scenario(30), RuntimeValues(topic="基线"))
    await relay(repo, _Registry(_FixedLLM(), observers=[single_obs]), run.run_id)
    single_p95 = _p95(single_obs.durations)

    # 5 并发各 30 条：聚合每轮编排耗时 p95
    conc_obs = _TurnDurationObserver()
    runs = [await create_run(repo, _scenario(30), RuntimeValues(topic=f"主题{i}")) for i in range(5)]
    await asyncio.gather(*(relay(repo, _Registry(_FixedLLM(), observers=[conc_obs]), r.run_id) for r in runs))
    conc_p95 = _p95(conc_obs.durations)

    # QG-5：并发下 p95 不劣化超过 2× 单会话基线（+ 小 epsilon 防抖）
    assert conc_p95 <= 2 * single_p95 + 0.005


# ── QG-4：延迟插桩（本地冒烟口径，宽松阈值防 CI 抖动）────────────────

@pytest.mark.asyncio
async def test_turn_overhead_p95_recorded(repo):
    run = await create_run(repo, _scenario(max_rounds=100), RuntimeValues(topic="主题"))
    observer = _TimingObserver()
    await relay(repo, _Registry(_FixedLLM(), observers=[observer]), run.run_id)
    deltas = [b - a for a, b in zip(observer.landed_at, observer.landed_at[1:])]
    p95_ms = _p95(deltas) * 1000
    assert p95_ms <= 100  # spec §6：每轮编排开销（不含生成）p95 ≤100 ms


@pytest.mark.asyncio
async def test_table_read_p95_recorded(repo):
    run = await create_run(repo, _scenario(max_rounds=500), RuntimeValues(topic="主题"))
    for i in range(500):
        await repo.append_turn(run.run_id, "a", f"发言{i}")
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        await repo.read_transcript(run.run_id)
        latencies.append(time.perf_counter() - t0)
    p95_ms = _p95(latencies) * 1000
    assert p95_ms <= 50  # spec §6：读完整共享转录 p95 ≤50 ms
