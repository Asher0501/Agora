"""T7 — 接力循环 relay（选人→判停→产出→落桌，ADR-0007，AC-05/06/07/07b/08/09/10b/18）。"""
from __future__ import annotations

import pytest

from agora.adapter.llm import FakeLLM
from agora.adapter.repository import Repository
from agora.config.schema import scenario_to_dict
from agora.relay import ProgressEvent, relay
from agora.types import RoleConfig, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "memory.db")
    yield r
    r.close()


class _Registry:
    def __init__(self, llm, capabilities=None, observers=None):
        self.llm = llm
        self.capabilities = capabilities or {}
        self.observers = observers or []


class _PromptLLM:
    """按 prompt 内容返回确定性输出（区分判收敛 / 选下一位 / 发言）。"""

    def __init__(self, verdict="CONTINUE", pick="NEXT:alice", speech="发言"):
        self.verdict = verdict
        self.pick = pick
        self.speech = speech

    async def complete(self, prompt: str) -> str:
        if "判收敛" in prompt:
            return self.verdict
        if "选下一位" in prompt:
            return self.pick
        return self.speech


class _Recorder:
    def __init__(self):
        self.events: list[ProgressEvent] = []

    def on_event(self, event: ProgressEvent) -> None:
        self.events.append(event)


def _speaker(*ids: str):
    return [
        RoleConfig(id=i, prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text")
        for i in ids
    ]


def _scenario(select_type="round_robin", stop_type="fixed_rounds", stop_max=3, roles=None, select_role=None, stop_judge=None):
    roles = roles or _speaker("alice", "bob")
    return ScenarioConfig(
        scenario="brainstorm",
        roles=roles,
        select=SelectConfig(type=select_type, role=select_role),
        stop=StopConfig(type=stop_type, max=stop_max, judge=stop_judge),
    )


async def _setup(repo, scenario, run_id="r1", topic="主题"):
    await repo.save_config(
        run_id,
        {"scenario": scenario_to_dict(scenario), "runtime": {"topic": topic, "stance": None, "extra": {}}},
    )
    await repo.save_status(run_id, {"status": "running", "current_seq": 0, "last_agent_id": None})
    return run_id


# ── AC-05/06/09 — 按序落桌、无重复、固定条数不多产 ─────────────────────

@pytest.mark.asyncio
async def test_round_robin_orders_labels_and_no_duplicate(repo):
    await _setup(repo, _scenario(stop_type="fixed_rounds", stop_max=3))
    outcome = await relay(repo, _Registry(FakeLLM(reply="发言")), "r1")
    assert [t.seq for t in outcome.transcript] == [1, 2, 3]
    assert [t.agent_id for t in outcome.transcript] == ["alice", "bob", "alice"]
    assert len(outcome.transcript) == 3  # AC-09：达条数即停，不多产
    assert outcome.recap.termination == "fixed_rounds"


# ── AC-08 — 裁判收敛写 verdict + recap ─────────────────────────────────

@pytest.mark.asyncio
async def test_llm_verdict_converges(repo):
    roles = _speaker("alice") + [RoleConfig(id="judge", prompt="判收敛：{history}", inject=["history"], output="verdict")]
    await _setup(repo, _scenario(stop_type="llm_verdict", stop_max=10, stop_judge="judge", roles=roles))
    outcome = await relay(repo, _Registry(_PromptLLM(verdict="CONVERGE:结论成立")), "r1")
    assert outcome.verdict is not None and outcome.verdict.converged is True
    assert outcome.verdict.conclusion == "结论成立"
    assert outcome.recap.termination == "converged"


# ── AC-10b — 上限未收敛标注「未收敛」───────────────────────────────────

@pytest.mark.asyncio
async def test_llm_verdict_caps_unconverged(repo):
    roles = _speaker("alice") + [RoleConfig(id="judge", prompt="判收敛：{history}", inject=["history"], output="verdict")]
    await _setup(repo, _scenario(stop_type="llm_verdict", stop_max=2, stop_judge="judge", roles=roles))
    outcome = await relay(repo, _Registry(_PromptLLM(verdict="CONTINUE")), "r1")
    assert outcome.recap.termination == "cap_unconverged"
    assert outcome.verdict is None  # 未收敛不写 verdict
    assert len(outcome.transcript) == 2


# ── AC-07 — 选人路由（llm_pick）───────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_pick_routes_to_selected_agent(repo):
    roles = [RoleConfig(id="mod", prompt="选下一位：{history}", inject=["history"], output="pick_next")] + _speaker("alice", "bob")
    await _setup(repo, _scenario(select_type="llm_pick", select_role="mod", stop_type="fixed_rounds", stop_max=1, roles=roles))
    outcome = await relay(repo, _Registry(_PromptLLM(pick="NEXT:bob")), "r1")
    assert outcome.transcript[0].agent_id == "bob"


# ── AC-07b — 无效选择重试后回退名单顺序 + 观测事件 ─────────────────────

@pytest.mark.asyncio
async def test_llm_pick_invalid_falls_back_with_events(repo):
    roles = [RoleConfig(id="mod", prompt="选下一位：{history}", inject=["history"], output="pick_next")] + _speaker("alice", "bob")
    await _setup(repo, _scenario(select_type="llm_pick", select_role="mod", stop_type="fixed_rounds", stop_max=1, roles=roles))
    outcome = await relay(repo, _Registry(_PromptLLM(pick="NEXT:ghost")), "r1")
    assert outcome.transcript[0].agent_id == "alice"  # 回退名单顺序 → 第一个发言人
    events = await repo.read_events("r1")
    invalid = [e for e in events if e.get("type") == "invalid_choice"]
    # 每次无效选择（首次 + 重试）都落盘为观测事件；ADR-0007 每轮选人→判停，
    # 末轮判停前仍会选人一次，故事件数 ≥ 2（本场景共 2 轮 × 2 次）。
    assert len(invalid) >= 2
    assert {e["reason"] for e in invalid} == {"选定的下一位不在名单内", "重试后仍无效"}


# ── OQ4 — 裁判解析失败：确定性回退 + 观测事件 + 达上限封顶 ─────────────

@pytest.mark.asyncio
async def test_verdict_parse_failure_emits_event_and_caps(repo):
    roles = _speaker("alice") + [RoleConfig(id="judge", prompt="判收敛：{history}", inject=["history"], output="verdict")]
    await _setup(repo, _scenario(stop_type="llm_verdict", stop_max=2, stop_judge="judge", roles=roles))
    outcome = await relay(repo, _Registry(_PromptLLM(verdict="乱码")), "r1")
    assert outcome.recap.termination == "cap_unconverged"  # 解析失败达上限仍封顶（AC-10b）
    assert len(outcome.transcript) == 2  # 不空转、不多产
    failures = [e for e in await repo.read_events("r1") if e.get("type") == "verdict_parse_failure"]
    assert len(failures) >= 1  # 每次解析失败落观测事件（不污染转录）


# ── AC-18 — 进度事件只携带本 run 内容 ─────────────────────────────────

@pytest.mark.asyncio
async def test_progress_events_only_carry_this_run(repo):
    await _setup(repo, _scenario(stop_type="fixed_rounds", stop_max=2), run_id="r1")
    recorder = _Recorder()
    await relay(repo, _Registry(FakeLLM(reply="发言"), observers=[recorder]), "r1")

    names = [e.name for e in recorder.events]
    assert names == [
        "run.turn_started", "run.turn_landed",
        "run.turn_started", "run.turn_landed",
        "run.stopped",
    ]
    # 事件只携带本 run id，payload 不含他会话内容
    for e in recorder.events:
        assert e.run_id == "r1"
        assert "other_run" not in e.payload
