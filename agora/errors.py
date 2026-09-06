"""中性领域错误（零 weave 依赖）— public-api.md §3.

统一信封 ``{code, message, details?}``；``code`` 用中性 ``agora.*`` snake_case
（ADR-0002「错误码中性化」，取代 brainstorm 的 ``session.*``）。
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """领域哨兵错误，携带稳定机器可读 ``code``。"""

    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        return d


# 9 个错误码登记（public-api.md §3 表，一一对应 AC）。
UNKNOWN_CAPABILITY = "agora.unknown_capability"  # AC-03
ROLE_DESCRIPTION_REQUIRED = "agora.role_description_required"  # AC-04
OUTPUT_JUDGE_MISMATCH = "agora.output_judge_mismatch"  # AC-13
SCENARIO_NOT_FOUND = "agora.scenario_not_found"  # AC-02b
RUNTIME_VALUE_REQUIRED = "agora.runtime_value_required"  # AC-02b
RUN_NOT_FOUND = "agora.run_not_found"  # AC-15b
RUN_CORRUPTED = "agora.run_corrupted"  # AC-15b
INVALID_STATE = "agora.invalid_state"  # 对已结束的会话继续接力（Flow 1）
TURN_ALREADY_PRODUCED = "agora.turn_already_produced"  # AC-06

# 跨会话/角色隔离（AC-16/17）是结构性（namespace 构造）而非运行时拒绝——不设哨兵。
