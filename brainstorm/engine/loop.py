"""Turn orchestration loop — run_session (AC-04/04b/09/14/15, ADR-0004)."""
from __future__ import annotations

import asyncio
from typing import Any

from ..business.errors import INVALID_STATE, ROUND_QUOTA_EXHAUSTED, DomainError
from ..business.protocols import (
    ProgressEvent,
    RoleContext,
    SchedulerContext,
    StopConditionContext,
)
from ..business.types import SessionOutcome, Speech
from ..weave_adapter.persona_agent import PersonaPrivateMemory
from .session import resume_session
from .stop import finalize_session


async def run_session(
    repository: Any,
    registry: Any,
    session_id: str,
    *,
    max_retries: int = 3,
    max_turns: int = 1000,
) -> SessionOutcome:
    """Drive the turn loop until the stop condition holds or a stop is requested.

    Each turn: pick the next speaker → generate (with retries) → append to the
    shared table → evaluate the stop condition. Progress events are emitted
    synchronously to registered consumers (observability only, ADR-0004).
    """
    session = await resume_session(repository, session_id)
    if session.status != "running":
        raise DomainError(INVALID_STATE, f"会话 {session_id} 已结束，无法继续运行")

    personas = session.personas
    scheduler = registry.get_scheduler(session.scheduler)
    stop_condition = registry.get_stop_condition(session.stop_condition.type)
    consumers = registry.consumers
    controller = registry.controller(session_id)
    controller.running = True

    history: list[Speech] = await repository.read_table(session_id)
    current_seq = len(history)
    last_speaker_id = history[-1].speaker_id if history else None
    selected_this_round: set[str] = set()
    converged = False
    conclusion: str | None = None

    def _emit(name: str, payload: dict[str, Any]) -> None:
        event = ProgressEvent(name=name, session_id=session_id, payload=payload)
        for consumer in consumers:
            consumer.on_event(event)

    try:
        for _turn in range(max_turns):
            await asyncio.sleep(0)  # yield so concurrent tasks (e.g. stop) interleave
            sched_ctx = SchedulerContext(
                session_id=session_id,
                topic=session.topic,
                personas=personas,
                last_speaker_id=last_speaker_id,
                current_seq=current_seq,
                history=history,
            )
            sched_decision = await scheduler.next_speaker(sched_ctx)

            # Router-declared convergence (AC-08/AC-10): end immediately.
            if sched_decision.converged:
                converged = True
                conclusion = sched_decision.conclusion
                break

            # Invalid router choice (AC-07b): record (fallback already applied).
            if sched_decision.invalid_choice:
                await repository.append_event(
                    session_id,
                    {
                        "type": "invalid_choice",
                        "speaker_id": sched_decision.invalid_choice,
                        "reason": "路由者选定无效",
                    },
                )

            speaker_id = sched_decision.speaker_id
            if speaker_id is None:
                continue

            # Round quota (AC-15): no re-select within one scheduler cycle.
            if speaker_id in selected_this_round:
                raise DomainError(
                    ROUND_QUOTA_EXHAUSTED,
                    f"参与者 {speaker_id} 本轮的发言名额已用",
                )
            selected_this_round.add(speaker_id)
            if len(selected_this_round) == len(personas):
                selected_this_round.clear()

            last_speaker_id = speaker_id
            _emit("session.turn_started", {"seq": current_seq + 1, "speaker_id": speaker_id})

            text = await _generate(
                repository, registry, session, speaker_id, history, max_retries
            )
            if text is None:
                await repository.append_event(
                    session_id,
                    {"type": "skip", "speaker_id": speaker_id, "reason": "生成失败"},
                )
                continue

            speech = await repository.append_speech(session_id, speaker_id, text)
            history.append(speech)
            current_seq = speech.seq
            _emit("session.speech_landed", {"seq": speech.seq, "speaker_id": speaker_id})

            stop_ctx = StopConditionContext(
                session_id=session_id,
                current_seq=current_seq,
                max_speeches=session.stop_condition.max_speeches,
                converged=converged,
                conclusion=conclusion,
                stop_requested=controller.stop_requested,
            )
            stop_decision = stop_condition.evaluate(stop_ctx)
            if stop_decision.stop:
                converged = stop_decision.converged
                conclusion = stop_decision.conclusion
                break
            if controller.stop_requested:
                converged = False
                conclusion = None
                break

        outcome = await finalize_session(repository, session_id, converged, conclusion)
        _emit("session.stopped", {"status": "stopped"})
        return outcome
    finally:
        controller.running = False
        controller.done.set()


async def _generate(
    repository: Any,
    registry: Any,
    session: Any,
    speaker_id: str,
    history: list[Speech],
    max_retries: int,
) -> str | None:
    role = registry.get_role(speaker_id)
    ctx = RoleContext(
        topic=session.topic,
        history=history,
        private_memory=PersonaPrivateMemory(repository, session.session_id, speaker_id),
    )
    for _attempt in range(max_retries):
        try:
            text = await role.speak(ctx)
            if text and text.strip():
                return text
        except Exception:
            continue
    return None
