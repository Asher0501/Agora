"""T12 — brainstorm.yaml 场景配置（纯 YAML，零引擎代码）。"""
from __future__ import annotations

from pathlib import Path

from agora.config import load_config

_SCENARIO_PATH = Path(__file__).resolve().parent.parent / "scenarios" / "brainstorm.yaml"


def test_brainstorm_yaml_loads_without_error():
    config = load_config(_SCENARIO_PATH)
    assert config.scenario == "brainstorm"
    assert [r.id for r in config.roles] == ["skeptic", "optimizer", "devil"]
    assert config.select.type == "round_robin"
    assert config.stop.type == "fixed_rounds"
    assert config.stop.max == 12
    assert all(r.output == "free_text" for r in config.roles)
