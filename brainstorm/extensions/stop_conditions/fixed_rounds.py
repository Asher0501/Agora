"""Default stop condition: end after ``max_speeches`` speeches (AC-09)."""
from __future__ import annotations

from brainstorm.business.protocols import Continue, Stop, StopConditionContext, StopDecision


class FixedRoundsStop:
    """Stops once ``current_seq`` reaches ``max_speeches`` (counted by speech)."""

    def evaluate(self, ctx: StopConditionContext) -> StopDecision:
        if ctx.max_speeches is not None and ctx.current_seq >= ctx.max_speeches:
            return Stop
        return Continue
