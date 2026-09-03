"""Manual stop — stop_session with in-flight safety (AC-11/AC-11b)."""
from __future__ import annotations

from typing import Any

from ..business.protocols import ProgressEvent
from ..business.types import SessionOutcome
from .session import resume_session


async def finalize_session(
    repository: Any,
    session_id: str,
    converged: bool = False,
    conclusion: str | None = None,
) -> SessionOutcome:
    """Mark the session stopped and return its full outcome (writes status + conclusion)."""
    history = await repository.read_table(session_id)
    await repository.update_session_status(
        session_id,
        {
            "status": "stopped",
            "current_seq": len(history),
            "last_speaker_id": history[-1].speaker_id if history else None,
        },
    )
    await repository.write_conclusion(
        session_id, {"converged": converged, "conclusion": conclusion}
    )
    return await build_outcome(repository, session_id)


async def build_outcome(repository: Any, session_id: str) -> SessionOutcome:
    """Read the persisted conclusion + table into a SessionOutcome (no writes)."""
    conclusion = await repository.load_conclusion(session_id) or {}
    return SessionOutcome(
        session_id=session_id,
        status="stopped",
        converged=bool(conclusion.get("converged", False)),
        conclusion=conclusion.get("conclusion"),
        speeches=await repository.read_table(session_id),
    )


async def stop_session(repository: Any, registry: Any, session_id: str) -> SessionOutcome:
    """Request a stop, waiting for any in-flight speech to land (AC-11/AC-11b)."""
    await resume_session(repository, session_id)  # raises NOT_FOUND if unknown
    controller = registry.controller(session_id)
    controller.stop_requested = True
    if controller.running:
        # A turn is in flight — wait for it to land and for the loop to finalize.
        await controller.done.wait()
        return await build_outcome(repository, session_id)
    outcome = await finalize_session(repository, session_id, converged=False, conclusion=None)
    _emit_stopped(registry, session_id)
    return outcome


def _emit_stopped(registry: Any, session_id: str) -> None:
    """Emit the stopped observability event (ADR-0004) on the direct-stop path."""
    event = ProgressEvent(name="session.stopped", session_id=session_id, payload={"status": "stopped"})
    for consumer in registry.consumers:
        consumer.on_event(event)
