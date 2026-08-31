"""Declarative assembly of the default extensions into a registry (AC-14)."""
from __future__ import annotations

from typing import Any

from .extensions.schedulers.round_robin import RoundRobinScheduler
from .extensions.stop_conditions.fixed_rounds import FixedRoundsStop
from .extensions.stop_conditions.manual import ManualStop


def assemble_defaults(registry: Any) -> None:
    """Register the default scheduler and stop conditions into ``registry``.

    ``registry`` is duck-typed: it only needs ``register_scheduler`` and
    ``register_stop_condition`` (the engine's Registry — assembled here so this
    module stays independent of the engine's concrete class).
    """
    registry.register_scheduler("round_robin", RoundRobinScheduler())
    registry.register_stop_condition("fixed_rounds", FixedRoundsStop())
    registry.register_stop_condition("manual", ManualStop())
