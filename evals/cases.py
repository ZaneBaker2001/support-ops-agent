from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class EvalCase:
    name: str
    question: str
    expected_severity: Severity
    expected_root_cause_keywords: list[str]
    expected_action_keywords: list[str]
    min_evidence_items: int = 1
    require_human_followup: bool | None = None


EVAL_CASES: list[EvalCase] = [
    EvalCase(
        name="password_reset_spike",
        question=(
            "We saw a spike in failed password reset tickets this week. "
            "Summarize likely causes and next actions."
        ),
        expected_severity="high",
        expected_root_cause_keywords=[
            "email",
            "token",
            "spam",
            "mobile",
            "csrf",
            "clock",
        ],
        expected_action_keywords=[
            "check",
            "validate",
            "review",
            "break down",
            "escalate",
            "logs",
        ],
        min_evidence_items=1,
        require_human_followup=True,
    ),
    EvalCase(
        name="password_reset_mobile",
        question=(
            "Customers report password reset failures on mobile web. "
            "What are likely causes and what should the support team do next?"
        ),
        expected_severity="high",
        expected_root_cause_keywords=[
            "mobile",
            "csrf",
            "session",
            "token",
        ],
        expected_action_keywords=[
            "review",
            "validate",
            "platform",
            "browser",
            "deploy",
        ],
        min_evidence_items=1,
        require_human_followup=True,
    ),
    EvalCase(
        name="general_mock_fallback",
        question=(
            "Give me a support operations summary for a generic issue with limited evidence."
        ),
        expected_severity="medium",
        expected_root_cause_keywords=[
            "mock",
            "insufficient",
            "model",
        ],
        expected_action_keywords=[
            "set",
            "test",
            "mock",
        ],
        min_evidence_items=1,
        require_human_followup=False,
    ),
]