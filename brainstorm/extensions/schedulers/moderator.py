"""Router-driven scheduler — the moderator persona adjudicates each turn (AC-07)."""
from __future__ import annotations

from brainstorm.business.protocols import (
    RoleContext,
    SchedulerContext,
    SchedulingDecision,
)

from .round_robin import RoundRobinScheduler

_CONVERGE_PREFIX = "CONVERGE:"
_NEXT_PREFIX = "NEXT:"


class ModeratorScheduler:
    """Asks the router role for the next speaker; falls back to round-robin.

    The router's decision text uses a small structured convention:
        ``NEXT: <persona_id>``     — pick that persona (must be on the roster)
        ``CONVERGE: <conclusion>`` — declare convergence with an optional conclusion
    Anything else (or an off-roster pick) falls back to round-robin. An off-roster
    pick is surfaced as ``invalid_choice`` so the loop can record it (AC-07b).
    """

    def __init__(self, router, fallback=None):
        self._router = router
        self._fallback = fallback if fallback is not None else RoundRobinScheduler()

    async def next_speaker(self, ctx: SchedulerContext) -> SchedulingDecision:
        role_ctx = RoleContext(topic=ctx.topic, history=ctx.history)
        decision_text = (await self._router.speak(role_ctx)).strip()

        if decision_text.startswith(_CONVERGE_PREFIX):
            conclusion = decision_text[len(_CONVERGE_PREFIX) :].strip() or None
            return SchedulingDecision(converged=True, conclusion=conclusion)

        if decision_text.startswith(_NEXT_PREFIX):
            persona_id = decision_text[len(_NEXT_PREFIX) :].strip()
            roster_ids = [p.persona_id for p in ctx.personas]
            if persona_id in roster_ids:
                return SchedulingDecision(speaker_id=persona_id)
            fallback = await self._fallback.next_speaker(ctx)
            return SchedulingDecision(
                speaker_id=fallback.speaker_id, invalid_choice=persona_id
            )

        fallback = await self._fallback.next_speaker(ctx)
        return SchedulingDecision(speaker_id=fallback.speaker_id)
