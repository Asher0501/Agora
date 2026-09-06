"""Contract tests — library-sdk surface + error sentinels (public-api §3/§5)."""
from __future__ import annotations

import inspect

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
)


def test_error_sentinels_match_contract():
    expected = {
        "agora.unknown_capability",
        "agora.role_description_required",
        "agora.output_judge_mismatch",
        "agora.scenario_not_found",
        "agora.runtime_value_required",
        "agora.run_not_found",
        "agora.run_corrupted",
        "agora.invalid_state",
        "agora.turn_already_produced",
    }
    actual = {
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
    assert actual == expected


def test_engine_operations_are_async():
    from agora.relay import relay
    from agora.session import create_run, read_transcript, resume_run, stop_run

    for op in (create_run, resume_run, relay, stop_run, read_transcript):
        assert inspect.iscoroutinefunction(op), op.__name__


def test_registry_provides_known_capabilities():
    from agora.wiring import build_registry

    reg = build_registry()
    assert "round_robin" in reg.known_capabilities()
    assert "llm_verdict" in reg.known_capabilities()
    assert "fixed_rounds" in reg.known_capabilities()
