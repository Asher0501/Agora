"""选人/判停原子（llm_pick / llm_verdict，moderator 的拆分等价）。"""
from __future__ import annotations

import pytest

from agora.atoms import LlmPickSelector, LlmVerdictTerminator
from agora.types import Agent, RoleConfig


class _SeqLLM:
    """按脚本序列返回决策（模拟 router）。"""

    def __init__(self, replies):
        self._replies = list(replies)
        self._i = 0

    async def complete(self, prompt: str) -> str:
        reply = self._replies[min(self._i, len(self._replies) - 1)]
        self._i += 1
        return reply


def _roster(*ids: str):
    return [Agent(run_id="r", agent_id=i, role_description="") for i in ids]


def _picker():
    return RoleConfig(id="mod", prompt="选下一位：{history}", inject=["history"], output="pick_next")


def _judge():
    return RoleConfig(id="judge", prompt="判收敛：{history}", inject=["history"], output="verdict")


@pytest.mark.asyncio
async def test_llm_pick_selects_valid_speaker():
    sel = LlmPickSelector(_SeqLLM(["NEXT: b"]), _picker())
    decision = await sel.next(_roster("a", "b"), [])
    assert decision.agent_id == "b"
    assert decision.converged is False


@pytest.mark.asyncio
async def test_llm_pick_invalid_choice_flags():
    sel = LlmPickSelector(_SeqLLM(["NEXT: zzz"]), _picker())
    decision = await sel.next(_roster("a", "b"), [])
    assert decision.invalid_choice == "zzz"


@pytest.mark.asyncio
async def test_llm_pick_converges_with_conclusion():
    sel = LlmPickSelector(_SeqLLM(["CONVERGE: 结论是X"]), _picker())
    decision = await sel.next(_roster("a", "b"), [])
    assert decision.converged is True
    assert decision.conclusion == "结论是X"


@pytest.mark.asyncio
async def test_llm_verdict_converge_and_cap():
    converge = LlmVerdictTerminator(_SeqLLM(["CONVERGE: 结论"]), _judge())
    d = await converge.should_stop({"current_seq": 1, "max": 20, "transcript": []})
    assert d.stop is True and d.converged is True and d.conclusion == "结论"

    cap = LlmVerdictTerminator(_SeqLLM(["CONTINUE"]), _judge())
    d2 = await cap.should_stop({"current_seq": 4, "max": 4, "transcript": []})
    assert d2.stop is True and d2.termination == "cap_unconverged" and d2.converged is False
