"""Default stop condition: continue until the host issues a stop (AC-11)."""
from __future__ import annotations

from brainstorm.business.protocols import Continue, Stop, StopConditionContext, StopDecision


class ManualStop:
    """Continues until an external stop instruction arrives (``stop_requested``)."""

    def evaluate(self, ctx: StopConditionContext) -> StopDecision:
        if ctx.stop_requested:
            return Stop
        return Continue
