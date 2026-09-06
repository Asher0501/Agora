"""菜单原子直接行为（round_robin / fixed_rounds / manual）。"""
from __future__ import annotations

import pytest

from agora.atoms import FixedRoundsTerminator, ManualTerminator, RoundRobinSelector
from agora.types import Agent, Turn


def _roster():
    return [
        Agent(run_id="r", agent_id="a", role_description="x"),
        Agent(run_id="r", agent_id="b", role_description="x"),
        Agent(run_id="r", agent_id="c", role_description="x"),
    ]


@pytest.mark.asyncio
async def test_round_robin_cycles_in_fixed_order():
    sel = RoundRobinSelector()
    roster = _roster()
    assert (await sel.next(roster, [])).agent_id == "a"
    assert (await sel.next(roster, [Turn(run_id="r", seq=1, agent_id="a", text="")])).agent_id == "b"
    assert (await sel.next(roster, [Turn(run_id="r", seq=1, agent_id="b", text="")])).agent_id == "c"
    assert (await sel.next(roster, [Turn(run_id="r", seq=1, agent_id="c", text="")])).agent_id == "a"  # wrap


@pytest.mark.asyncio
async def test_fixed_rounds_stops_at_max():
    term = FixedRoundsTerminator()
    assert (await term.should_stop({"current_seq": 2, "max": 3})).stop is False
    assert (await term.should_stop({"current_seq": 3, "max": 3})).stop is True


@pytest.mark.asyncio
async def test_manual_continues_until_stop_requested():
    term = ManualTerminator()
    assert (await term.should_stop({"current_seq": 0})).stop is False
    assert (await term.should_stop({"current_seq": 0, "stop_requested": True})).stop is True
