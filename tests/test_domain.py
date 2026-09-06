"""T1 — agora 领域层：中性类型、错误码、命名空间（零 weave 依赖）。

镜像 brainstorm 的 ``test_domain.py`` 隔离断言：agora 的领域基石
（types/errors/namespaces）必须零 weave 依赖（SAD §2 单向依赖，ADR-0002）。
"""
from __future__ import annotations

import pathlib
from dataclasses import FrozenInstanceError

import pytest

from agora.errors import (
    INVALID_STATE,
    OUTPUT_JUDGE_MISMATCH,
    ROLE_DESCRIPTION_REQUIRED,
    RUN_CORRUPTED,
    RUN_NOT_FOUND,
    RUNTIME_VALUE_REQUIRED,
    SCENARIO_NOT_FOUND,
    TURN_ALREADY_PRODUCED,
    UNKNOWN_CAPABILITY,
    DomainError,
)
from agora.namespaces import (
    STATE_KEY_CONFIG,
    STATE_KEY_RECAP,
    STATE_KEY_STATUS,
    STATE_KEY_VERDICT,
    agent_state_ns,
    agent_stream_ns,
    run_events_ns,
    run_state_ns,
    run_stream_ns,
)
from agora.types import (
    Agent,
    Recap,
    RoleConfig,
    Run,
    RunOutcome,
    RuntimeValues,
    ScenarioConfig,
    SelectConfig,
    StopConfig,
    SummaryConfig,
    Turn,
    Verdict,
)

# ── 命名空间构造器 — data-model §Namespace scheme ──────────────────────

def test_namespace_builders_match_scheme():
    assert run_stream_ns("r1") == "agora:r1:stream"
    assert run_state_ns("r1") == "agora:r1:state"
    assert run_events_ns("r1") == "agora:r1:events:stream"
    assert agent_stream_ns("r1", "alice") == "agora:r1:alice:stream"
    assert agent_state_ns("r1", "alice") == "agora:r1:alice:state"


def test_state_keys_registered():
    assert STATE_KEY_CONFIG == "config"
    assert STATE_KEY_STATUS == "status"
    assert STATE_KEY_VERDICT == "verdict"
    assert STATE_KEY_RECAP == "recap"


# ── DomainError 信封 — public-api.md §3 ────────────────────────────────

def test_domain_error_to_dict_no_details():
    err = DomainError("agora.run_not_found", "会话不存在")
    assert err.to_dict() == {"code": "agora.run_not_found", "message": "会话不存在"}


def test_domain_error_to_dict_with_details():
    err = DomainError("agora.run_not_found", "会话不存在", {"run_id": "r1"})
    assert err.to_dict()["details"] == {"run_id": "r1"}


def test_nine_error_codes_registered_with_neutral_prefix():
    codes = {
        UNKNOWN_CAPABILITY,
        ROLE_DESCRIPTION_REQUIRED,
        OUTPUT_JUDGE_MISMATCH,
        SCENARIO_NOT_FOUND,
        RUNTIME_VALUE_REQUIRED,
        RUN_NOT_FOUND,
        RUN_CORRUPTED,
        INVALID_STATE,
        TURN_ALREADY_PRODUCED,
    }
    assert len(codes) == 9
    assert all(code.startswith("agora.") for code in codes)


# ── frozen dataclass 类型 — public-api.md §2 ────────────────────────────

def _scenario():
    return ScenarioConfig(
        scenario="brainstorm",
        roles=[RoleConfig(id="alice", prompt="产品视角")],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="fixed_rounds", max=3),
    )


def test_run_is_frozen_dataclass():
    run = Run(
        run_id="r1",
        scenario=_scenario(),
        runtime=RuntimeValues(topic="示例主题"),
    )
    assert run.run_id == "r1"
    assert run.status == "running"
    assert run.current_seq == 0
    assert run.verdict is None
    assert run.recap is None
    with pytest.raises(FrozenInstanceError):
        run.run_id = "r2"  # type: ignore[misc]


def test_turn_agent_verdict_recap_shapes():
    turn = Turn(run_id="r1", seq=1, agent_id="alice", text="发言")
    assert turn.seq == 1 and turn.agent_id == "alice"

    agent = Agent(run_id="r1", agent_id="alice", role_description="产品视角")
    assert agent.role_description == "产品视角"

    verdict = Verdict(converged=True, conclusion="结论")
    assert verdict.converged and verdict.conclusion == "结论"

    recap = Recap(termination="converged", recap="总结")
    assert recap.termination == "converged"


def test_run_outcome_carries_transcript():
    outcome = RunOutcome(
        run_id="r1",
        status="stopped",
        verdict=Verdict(converged=True, conclusion="结论"),
        recap=Recap(termination="converged", recap="总结"),
        transcript=[Turn(run_id="r1", seq=1, agent_id="alice", text="发言")],
    )
    assert len(outcome.transcript) == 1


def test_summary_config_minimal_shape():
    summary = SummaryConfig(role="judge", key="summary", window=20)
    assert summary.role == "judge"
    assert summary.key == "summary"
    assert summary.window == 20


# ── 零 weave 依赖 — SAD §2 / ADR-0002 ──────────────────────────────────

def test_agora_domain_has_no_weave_import():
    agora_dir = pathlib.Path(__file__).resolve().parent.parent / "agora"
    for name in ("types.py", "errors.py", "namespaces.py"):
        path = agora_dir / name
        assert path.exists(), f"{name} missing"
        text = path.read_text(encoding="utf-8")
        assert "import weave" not in text and "from weave" not in text, name
