"""Contract tests — library-sdk surface + error sentinels (public-api.md §3/§5)."""

import inspect

import brainstorm
from brainstorm import Registry


def test_error_sentinels_match_contract():
    expected = {
        "session.topic_required",
        "session.insufficient_personas",
        "session.persona_role_required",
        "session.round_quota_exhausted",
        "session.not_found",
        "session.invalid_state",
    }
    actual = {
        brainstorm.TOPIC_REQUIRED,
        brainstorm.INSUFFICIENT_PERSONAS,
        brainstorm.PERSONA_ROLE_REQUIRED,
        brainstorm.ROUND_QUOTA_EXHAUSTED,
        brainstorm.NOT_FOUND,
        brainstorm.INVALID_STATE,
    }
    assert actual == expected


def test_engine_operations_are_async():
    for name in ("create_session", "resume_session", "run_session", "stop_session", "read_table"):
        op = getattr(brainstorm, name)
        assert inspect.iscoroutinefunction(op), name


def test_registry_extension_points_exist():
    reg = Registry()
    for name in (
        "register_role",
        "register_scheduler",
        "register_stop_condition",
        "register_consumer",
    ):
        assert callable(getattr(reg, name)), name
