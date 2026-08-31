"""Convergence stop condition — end on the router's verdict, else cap (AC-08/10/10b)."""
from __future__ import annotations

from brainstorm.business.protocols import Continue, Stop, StopConditionContext, StopDecision


class ConvergenceStop:
    """Stops when converged (with the router's conclusion) or at ``max_speeches``."""

    def evaluate(self, ctx: StopConditionContext) -> StopDecision:
        if ctx.converged:
            return StopDecision(stop=True, conclusion=ctx.conclusion, converged=True)
        if ctx.max_speeches is not None and ctx.current_seq >= ctx.max_speeches:
            return Stop  # forced end, marked not-converged (AC-10b)
        return Continue
