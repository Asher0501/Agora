"""T2 — 五原子协议、产出/解析、闭集菜单原子（零 weave 依赖）。"""
from __future__ import annotations

import pytest

from agora.atoms import (
    MENU,
    FixedRoundsTerminator,
    LlmPickSelector,
    LlmVerdictTerminator,
    ManualTerminator,
    OutputSpec,
    Parsed,
    RoundRobinSelector,
    Selection,
    StopDecision,
    parse,
    render,
)
from agora.types import Agent, RoleConfig, Turn

# ── 产出解析 — public-api §4 ③ ─────────────────────────────────────────

def test_parse_free_text_returns_original():
    assert parse("随便说说", OutputSpec(kind="free_text")) == Parsed(text="随便说说")


def test_parse_pick_next_hits_next():
    p = parse("NEXT:alice", OutputSpec(kind="pick_next"))
    assert p.next_agent_id == "alice"
    assert not p.parse_failure


def test_parse_pick_next_hits_converge():
    p = parse("CONVERGE:结论成立", OutputSpec(kind="pick_next"))
    assert p.converged is True
    assert p.conclusion == "结论成立"


def test_parse_verdict_hits_converge():
    p = parse("CONVERGE:正方胜", OutputSpec(kind="verdict"))
    assert p.converged is True
    assert p.conclusion == "正方胜"


def test_parse_verdict_hits_continue():
    p = parse("CONTINUE", OutputSpec(kind="verdict"))
    assert p.converged is False
    assert not p.parse_failure


def test_parse_failure_sets_flag():
    assert parse("乱码", OutputSpec(kind="pick_next")).parse_failure is True
    assert parse("乱码", OutputSpec(kind="verdict")).parse_failure is True


# ── 模板渲染 — public-api §4 ② ─────────────────────────────────────────

def _turns(n=5):
    return [Turn(run_id="r", seq=i, agent_id="a", text=f"第{i}条") for i in range(1, n + 1)]


def test_render_injects_fields():
    out = render("主题：{topic}", {"topic": "测试"}, 0)
    assert out == "主题：测试"


def test_render_truncates_history_to_window():
    out = render("历史：\n{history}", {"history": _turns(5)}, 2)
    assert "第4条" in out and "第5条" in out
    assert "第3条" not in out


def test_render_formats_history_lines():
    out = render("{history}", {"history": _turns(2)}, 0)
    assert "a: 第1条" in out and "a: 第2条" in out


# ── round_robin / fixed_rounds — 纯状态函数 ────────────────────────────

@pytest.mark.asyncio
async def test_round_robin_cycles_roster():
    roster = [
        Agent(run_id="r", agent_id="a", role_description=""),
        Agent(run_id="r", agent_id="b", role_description=""),
    ]
    sel = RoundRobinSelector()
    transcript: list[Turn] = []
    assert (await sel.next(roster, transcript)).agent_id == "a"
    transcript.append(Turn(run_id="r", seq=1, agent_id="a", text=""))
    assert (await sel.next(roster, transcript)).agent_id == "b"
    transcript.append(Turn(run_id="r", seq=2, agent_id="b", text=""))
    assert (await sel.next(roster, transcript)).agent_id == "a"


@pytest.mark.asyncio
async def test_fixed_rounds_stops_at_max():
    term = FixedRoundsTerminator()
    assert (await term.should_stop({"current_seq": 2, "max": 3})).stop is False
    d = await term.should_stop({"current_seq": 3, "max": 3})
    assert d.stop is True and d.termination == "fixed_rounds"


# ── llm_pick / llm_verdict — 仅依赖 LLM 协议 ────────────────────────────

class _FixedLLM:
    def __init__(self, reply: str):
        self.reply = reply

    async def complete(self, prompt: str) -> str:
        return self.reply


def _roster(*ids: str):
    return [Agent(run_id="r", agent_id=i, role_description="") for i in ids]


@pytest.mark.asyncio
async def test_llm_pick_selects_valid_agent():
    picker = RoleConfig(id="mod", prompt="选下一位：{history}", output="pick_next")
    sel = LlmPickSelector(_FixedLLM("NEXT:bob"), picker)
    s = await sel.next(_roster("alice", "bob"), [])
    assert s.agent_id == "bob"


@pytest.mark.asyncio
async def test_llm_pick_flags_off_roster_choice():
    picker = RoleConfig(id="mod", prompt="{history}", output="pick_next")
    sel = LlmPickSelector(_FixedLLM("NEXT:ghost"), picker)
    s = await sel.next(_roster("alice"), [])
    assert s.invalid_choice == "ghost"
    assert s.agent_id is None


@pytest.mark.asyncio
async def test_llm_verdict_converges():
    judge = RoleConfig(id="judge", prompt="{history}", output="verdict")
    term = LlmVerdictTerminator(_FixedLLM("CONVERGE:正方"), judge)
    d = await term.should_stop({"current_seq": 1, "max": 20, "transcript": []})
    assert d.stop is True and d.termination == "converged" and d.converged


@pytest.mark.asyncio
async def test_llm_verdict_caps_when_unconverged_at_max():
    judge = RoleConfig(id="judge", prompt="{history}", output="verdict")
    term = LlmVerdictTerminator(_FixedLLM("CONTINUE"), judge)
    d = await term.should_stop({"current_seq": 20, "max": 20, "transcript": []})
    assert d.stop is True and d.termination == "cap_unconverged"


@pytest.mark.asyncio
async def test_manual_stops_on_flag():
    term = ManualTerminator()
    assert (await term.should_stop({})).stop is False
    assert (await term.should_stop({"stop_requested": True})).stop is True


@pytest.mark.asyncio
async def test_llm_verdict_parse_failure_at_cap_still_stops():
    # AC-10b：即便裁判产出解析失败，达条数上限也强制结束（不空转）
    judge = RoleConfig(id="judge", prompt="{history}", output="verdict")
    term = LlmVerdictTerminator(_FixedLLM("乱码"), judge)
    d = await term.should_stop({"current_seq": 5, "max": 5, "transcript": []})
    assert d.stop is True and d.termination == "cap_unconverged"
    assert d.parse_failure is True  # 仍标记解析失败（relay 落观测事件）


# ── 闭集菜单 — public-api §4 表 ────────────────────────────────────────

def test_menu_lists_five_atoms():
    assert MENU == {"round_robin", "llm_pick", "fixed_rounds", "llm_verdict", "manual"}


def test_parse_failure_and_stop_decision_shapes():
    assert Parsed().parse_failure is False
    assert Selection().agent_id is None
    assert StopDecision(stop=True).termination is None
