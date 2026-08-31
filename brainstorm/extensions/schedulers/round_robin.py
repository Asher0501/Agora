"""Default scheduler: fixed round-robin over the roster."""
from __future__ import annotations

from brainstorm.business.protocols import SchedulerContext


class RoundRobinScheduler:
    """Picks the next speaker by cycling the roster in a fixed order."""

    def next_speaker(self, ctx: SchedulerContext) -> str:
        ids = [p.persona_id for p in ctx.personas]
        if ctx.last_speaker_id is None or ctx.last_speaker_id not in ids:
            return ids[0]
        return ids[(ids.index(ctx.last_speaker_id) + 1) % len(ids)]
