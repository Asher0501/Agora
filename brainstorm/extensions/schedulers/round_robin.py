"""Default scheduler: fixed round-robin over the roster."""
from __future__ import annotations

from brainstorm.business.protocols import SchedulerContext, SchedulingDecision


class RoundRobinScheduler:
    """Picks the next speaker by cycling the roster in a fixed order."""

    async def next_speaker(self, ctx: SchedulerContext) -> SchedulingDecision:
        ids = [p.persona_id for p in ctx.personas]
        if ctx.last_speaker_id is None or ctx.last_speaker_id not in ids:
            return SchedulingDecision(speaker_id=ids[0])
        return SchedulingDecision(
            speaker_id=ids[(ids.index(ctx.last_speaker_id) + 1) % len(ids)]
        )
