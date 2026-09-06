"""T11 — 包导出与 CLI 入口冒烟测试。"""
from __future__ import annotations

import importlib

import agora


def test_agora_imports():
    assert agora is not None


def test_public_submodules_accessible():
    for name in ("types", "errors", "namespaces", "atoms", "relay", "session", "config", "extension"):
        mod = importlib.import_module(f"agora.{name}")
        assert mod is not None


def test_adapter_subpackage_accessible():
    importlib.import_module("agora.adapter.repository")
    importlib.import_module("agora.adapter.llm")


def test_cli_entry_point_imports():
    from agora.cli import main

    assert callable(main)


def test_wiring_builds_registry():
    from agora.wiring import build_registry

    reg = build_registry()
    assert "round_robin" in reg.known_capabilities()
    assert "fixed_rounds" in reg.known_capabilities()
