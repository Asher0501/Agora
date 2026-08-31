"""T2 — domain types, error sentinels, extension protocols (zero weave)."""

import inspect
import pathlib
from typing import get_type_hints

import pytest

from brainstorm.business.errors import (
    INSUFFICIENT_PERSONAS,
    PERSONA_ROLE_REQUIRED,
    TOPIC_REQUIRED,
    DomainError,
)
from brainstorm.business.protocols import Consumer, Role, Scheduler, StopCondition
from brainstorm.business.types import (
    PersonaConfig,
    SessionConfig,
    StopConditionConfig,
)
from brainstorm.business.validation import validate_config


def _config(topic="示例主题", personas=None, scheduler="round_robin", stop_type="manual"):
    personas = personas or [
        PersonaConfig(persona_id="alice", name="Alice", role_description="产品视角"),
        PersonaConfig(persona_id="bob", name="Bob", role_description="技术视角"),
    ]
    return SessionConfig(
        topic=topic,
        personas=personas,
        scheduler=scheduler,
        stop_condition=StopConditionConfig(type=stop_type),
    )


# ── validate_config — AC-02 / AC-03 / AC-13 ──────────────────────────

def test_empty_topic_is_rejected_with_topic_required():
    with pytest.raises(DomainError) as exc:
        validate_config(_config(topic=""))
    assert exc.value.code == TOPIC_REQUIRED


def test_whitespace_topic_is_rejected():
    with pytest.raises(DomainError) as exc:
        validate_config(_config(topic="   "))
    assert exc.value.code == TOPIC_REQUIRED


def test_fewer_than_two_unique_personas_is_rejected():
    dupes = [
        PersonaConfig(persona_id="alice", name="Alice", role_description="产品视角"),
        PersonaConfig(persona_id="alice", name="Alice", role_description="产品视角"),
    ]
    with pytest.raises(DomainError) as exc:
        validate_config(_config(personas=dupes))
    assert exc.value.code == INSUFFICIENT_PERSONAS


def test_missing_role_description_is_rejected():
    personas = [
        PersonaConfig(persona_id="alice", name="Alice", role_description="产品视角"),
        PersonaConfig(persona_id="bob", name="Bob", role_description=""),
    ]
    with pytest.raises(DomainError) as exc:
        validate_config(_config(personas=personas))
    assert exc.value.code == PERSONA_ROLE_REQUIRED


def test_valid_config_passes():
    validate_config(_config())  # must not raise


# ── protocols sign as documented — public-api.md §4 ───────────────────

def test_extension_protocols_sign_as_documented():
    assert inspect.iscoroutinefunction(Role.speak)
    speak = inspect.signature(Role.speak)
    assert list(speak.parameters) == ["self", "ctx"]
    assert get_type_hints(Role.speak)["return"] is str

    sched = inspect.signature(Scheduler.next_speaker)
    assert list(sched.parameters) == ["self", "ctx"]
    assert get_type_hints(Scheduler.next_speaker)["return"] is str

    stop = inspect.signature(StopCondition.evaluate)
    assert list(stop.parameters) == ["self", "ctx"]

    consume = inspect.signature(Consumer.on_event)
    assert list(consume.parameters) == ["self", "event"]


# ── zero weave dependency — sad §2 / ADR-0002 ──────────────────────────

def test_business_has_no_weave_import():
    business_dir = (
        pathlib.Path(__file__).resolve().parent.parent / "brainstorm" / "business"
    )
    files = list(business_dir.glob("*.py"))
    assert files, "business package is empty"
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert "import weave" not in text and "from weave" not in text, path.name
