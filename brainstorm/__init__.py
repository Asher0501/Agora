"""brainstorm — multi-persona brainstorm engine.

Stable kernel (session lifecycle, turn loop, shared table, extension registry)
with four pluggable extension points (role / scheduler / stop-condition / consumer).

Layering (see docs/features/brainstorm/sad.md §5):
    business/       — pure domain types, zero weave dependency
    engine/         — kernel orchestration
    extensions/     — default pluggable implementations
    weave_adapter/  — the single weave integration point (persistence + LLM)
    cli/            — command-line driver
"""

__version__ = "0.1.0"
