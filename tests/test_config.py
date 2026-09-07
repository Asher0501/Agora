"""T5 — 配置 schema 与加载时校验（AC-03/04/13 + 保留字 + 占位符）。"""
from __future__ import annotations

import pytest
import yaml

from agora.config import load_config, parse_config, validate_config
from agora.errors import (
    INVALID_CONFIG,
    INVALID_PLACEHOLDER,
    OUTPUT_JUDGE_MISMATCH,
    RESERVED_AGENT_ID,
    ROLE_DESCRIPTION_REQUIRED,
    UNKNOWN_CAPABILITY,
    DomainError,
)


def _raw(**overrides):
    raw = {
        "scenario": "brainstorm",
        "roles": [
            {"id": "alice", "prompt": "你是{name}。主题：{topic}", "inject": ["topic"], "window": 20, "output": "free_text"},
            {"id": "judge", "prompt": "判收敛：{history}", "inject": ["history"], "output": "verdict"},
        ],
        "select": {"type": "round_robin"},
        "stop": {"type": "llm_verdict", "judge": "judge", "max": 20},
    }
    raw.update(overrides)
    return raw


# ── 合法配置 ───────────────────────────────────────────────────────────

def test_valid_config_parses():
    c = parse_config(_raw())
    assert c.scenario == "brainstorm"
    assert len(c.roles) == 2
    assert c.stop.type == "llm_verdict" and c.stop.judge == "judge"
    assert c.select.type == "round_robin"


def test_valid_config_passes_validate():
    validate_config(parse_config(_raw()))  # must not raise


# ── AC-03 未知能力 ─────────────────────────────────────────────────────

def test_unknown_select_capability_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(select={"type": "telepathy"}))
    assert exc.value.code == UNKNOWN_CAPABILITY


def test_unknown_stop_capability_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "mood_ring"}))
    assert exc.value.code == UNKNOWN_CAPABILITY


# ── AC-04 角色描述必填 ─────────────────────────────────────────────────

def test_missing_role_description_rejected():
    raw = _raw()
    raw["roles"][0]["prompt"] = ""
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == ROLE_DESCRIPTION_REQUIRED


# ── AC-13 output 与 select/stop 匹配 ────────────────────────────────────

def test_judge_with_free_text_output_rejected():
    raw = _raw()
    raw["roles"][1]["output"] = "free_text"  # judge 应为 verdict
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == OUTPUT_JUDGE_MISMATCH


def test_picker_with_wrong_output_rejected():
    raw = _raw()
    raw["select"] = {"type": "llm_pick", "role": "judge"}  # judge 是 verdict，不是 pick_next
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == OUTPUT_JUDGE_MISMATCH


# ── 保留字 / 占位符 ────────────────────────────────────────────────────

def test_reserved_events_agent_id_rejected():
    raw = _raw()
    raw["roles"][0]["id"] = "events"
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == RESERVED_AGENT_ID


def test_placeholder_not_in_inject_rejected():
    raw = _raw()
    raw["roles"][0]["prompt"] = "主题：{topic} 立场：{stance}"  # stance 未在 inject
    raw["roles"][0]["inject"] = ["topic"]
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == INVALID_PLACEHOLDER


def test_unknown_inject_field_rejected():
    raw = _raw()
    raw["roles"][0]["inject"] = ["topic", "mood"]
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == INVALID_PLACEHOLDER


# ── max/window 数值 ────────────────────────────────────────────────────

def test_nonpositive_max_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "fixed_rounds", "max": 0}))
    assert exc.value.code == INVALID_CONFIG


def test_fixed_rounds_requires_max():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "fixed_rounds"}))
    assert exc.value.code == INVALID_CONFIG


def test_llm_verdict_requires_max():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "llm_verdict", "judge": "judge"}))
    assert exc.value.code == INVALID_CONFIG


# ── 标量类型校验（ADR-0005 / QG-1：不抛裸异常）──────────────────────────

def test_numeric_string_max_coerced():
    c = parse_config(_raw(stop={"type": "fixed_rounds", "max": "3"}))
    assert c.stop.max == 3


def test_non_numeric_max_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "fixed_rounds", "max": "abc"}))
    assert exc.value.code == INVALID_CONFIG


def test_non_numeric_window_rejected():
    raw = _raw()
    raw["roles"][0]["window"] = "abc"
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == INVALID_CONFIG


# ── T25 — summary.key 限定 summary.role ────────────────────────────────

def test_summary_key_scoped_to_summary_role():
    raw = _raw()
    raw["summary"] = {"role": "alice", "key": "memo"}
    # bob（非 summary 角色）引用 {memo} → 加载时拒绝
    raw["roles"].append({"id": "bob", "prompt": "我的备忘：{memo}", "inject": [], "output": "free_text"})
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == INVALID_PLACEHOLDER


# ── T28 — 结构形状守卫（不抛裸 AttributeError/TypeError）───────────────

def test_roles_scalar_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(roles="oops"))
    assert exc.value.code == INVALID_CONFIG


def test_roles_null_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(roles=None))
    assert exc.value.code == INVALID_CONFIG


def test_roles_mapping_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(roles={"id": "x"}))
    assert exc.value.code == INVALID_CONFIG


def test_select_scalar_rejected():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(select="round_robin"))
    assert exc.value.code == INVALID_CONFIG


# ── T29 — llm_verdict/llm_pick 必填 judge/role ─────────────────────────

def test_llm_verdict_requires_judge():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(stop={"type": "llm_verdict", "max": 5}))
    assert exc.value.code == INVALID_CONFIG


def test_llm_pick_requires_role():
    with pytest.raises(DomainError) as exc:
        parse_config(_raw(select={"type": "llm_pick"}))
    assert exc.value.code == INVALID_CONFIG


# ── T31 — roles[].output 闭集枚举（非法值加载时拒，无静默空跑）──────────

def test_unknown_output_rejected():
    raw = _raw()
    raw["roles"][0]["output"] = "freetext"  # 拼写错误，非闭集枚举
    with pytest.raises(DomainError) as exc:
        parse_config(raw)
    assert exc.value.code == INVALID_CONFIG


# ── 扩展能力注入（T6 前置：known_capabilities 注入）────────────────────

def test_custom_capability_accepted_when_registered():
    known = {"round_robin", "llm_pick", "fixed_rounds", "llm_verdict", "manual", "custom_sel"}
    c = parse_config(_raw(select={"type": "custom_sel"}), known_capabilities=known)
    assert c.select.type == "custom_sel"


# ── load_config 读 YAML ────────────────────────────────────────────────

def test_load_config_reads_yaml(tmp_path):
    path = tmp_path / "s.yaml"
    path.write_text(yaml.safe_dump(_raw(), allow_unicode=True), encoding="utf-8")
    c = load_config(path)
    assert c.scenario == "brainstorm"
