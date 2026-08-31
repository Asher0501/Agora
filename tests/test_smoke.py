"""T1 scaffold smoke test — the package and its five subpackages import cleanly."""

import importlib


def test_brainstorm_imports():
    import brainstorm  # noqa: F401


def test_subpackages_import():
    for subpackage in ("business", "engine", "extensions", "weave_adapter", "cli"):
        importlib.import_module(f"brainstorm.{subpackage}")
