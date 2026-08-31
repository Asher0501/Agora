"""T6 — YAML config loader (AC-12/AC-13) + declarative wiring (AC-14)."""

import pytest
import yaml

from brainstorm.business.errors import PERSONA_ROLE_REQUIRED, DomainError
from brainstorm.business.types import SessionConfig
from brainstorm.config_loader import load_config, load_personas, parse_config
from brainstorm.extensions.schedulers.round_robin import RoundRobinScheduler
from brainstorm.extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from brainstorm.extensions.stop_conditions.manual import ManualStop
from brainstorm.wiring import assemble_defaults


def test_parse_config_from_dict():
    raw = {
        "topic": "如何提升留存",
        "personas": [
            {"persona_id": "a", "name": "A", "role_description": "产品"},
            {"persona_id": "b", "name": "B", "role_description": "技术"},
        ],
        "scheduler": "round_robin",
        "stop_condition": {"type": "fixed_rounds", "max_speeches": 5},
    }
    cfg = parse_config(raw)
    assert isinstance(cfg, SessionConfig)
    assert cfg.topic == "如何提升留存"
    assert [p.persona_id for p in cfg.personas] == ["a", "b"]
    assert cfg.scheduler == "round_robin"
    assert cfg.stop_condition.type == "fixed_rounds"
    assert cfg.stop_condition.max_speeches == 5


def test_load_config_rejects_missing_role_description(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "topic": "主题",
                "personas": [
                    {"persona_id": "a", "name": "A", "role_description": "产品"},
                    {"persona_id": "b", "name": "B"},  # missing role_description
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DomainError) as exc:
        load_config(p)
    assert exc.value.code == PERSONA_ROLE_REQUIRED


def test_load_personas_list(tmp_path):
    p = tmp_path / "personas.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "personas": [
                    {"persona_id": "a", "name": "A", "role_description": "产品"},
                    {"persona_id": "b", "name": "B", "role_description": "技术"},
                ]
            }
        ),
        encoding="utf-8",
    )
    personas = load_personas(p)
    assert [x.persona_id for x in personas] == ["a", "b"]


class _FakeRegistry:
    def __init__(self):
        self.schedulers = {}
        self.stop_conditions = {}

    def register_scheduler(self, name, instance):
        self.schedulers[name] = instance

    def register_stop_condition(self, name, instance):
        self.stop_conditions[name] = instance


def test_assemble_defaults_registers():
    reg = _FakeRegistry()
    assemble_defaults(reg)
    assert isinstance(reg.schedulers["round_robin"], RoundRobinScheduler)
    assert isinstance(reg.stop_conditions["fixed_rounds"], FixedRoundsStop)
    assert isinstance(reg.stop_conditions["manual"], ManualStop)
