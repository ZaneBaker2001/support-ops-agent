from __future__ import annotations

from functools import lru_cache

from app.agent import build_agent
from app.config import get_settings
from app.schemas import Evidence, FinalAnswer


@lru_cache(maxsize=1)
def get_agent():
    return build_agent()


def mock_answer(question: str) -> FinalAnswer:
    q = question.lower()

    if "password reset" in q or "reset" in q:
        return FinalAnswer(
            summary=(
                "This week’s failures appear concentrated in the password-reset flow. "
                "The most likely causes are delayed delivery, invalid or expiring tokens, "
                "mobile/browser flow issues, and spam filtering for some recipients."
            ),
            severity="high",
            likely_root_causes=[
                "Email provider throttling or delayed delivery",
                "Expired, invalid, or incorrectly signed reset tokens",
                "Mobile web flow errors or stale CSRF/session state",
                "Spam filtering or low sender reputation",
            ],
            recommended_actions=[
                "Check email provider logs for bounces, throttling, and delivery delays",
                "Validate token TTL, signing secrets, and auth-service clock synchronization",
                "Review recent auth and mobile-web deploys",
                "Break down failures by tenant, platform, browser, and geography",
                "Escalate unresolved high-priority auth tickets to engineering",
            ],
            evidence=[
                Evidence(
                    source="password-reset-runbook.md",
                    snippet="Email provider throttling can delay delivery of password reset emails.",
                ),
                Evidence(
                    source="password-reset-runbook.md",
                    snippet="Expired or incorrectly signed reset tokens can happen after auth-service clock drift or stale signing secrets.",
                ),
            ],
            needs_human_followup=True,
        )

    return FinalAnswer(
        summary="Mock mode is enabled. This is a deterministic placeholder response for local development.",
        severity="medium",
        likely_root_causes=["Insufficient live model access in mock mode"],
        recommended_actions=[
            "Set MODEL_PROVIDER=ollama or provide OPENAI_API_KEY for live model behavior",
            "Keep USE_MOCK_LLM=true for UI and API integration testing",
        ],
        evidence=[
            Evidence(
                source="mock_service",
                snippet="Returned from local deterministic fallback.",
            )
        ],
        needs_human_followup=False,
    )


def ask_agent(question: str) -> FinalAnswer:
    settings = get_settings()

    if settings.use_mock_llm or settings.model_provider.lower() == "mock":
        return mock_answer(question)

    agent = get_agent()
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )

    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError(
            f"Agent returned no structured_response. Raw keys: {list(result.keys())}"
        )

    if isinstance(structured, FinalAnswer):
        return structured

    return FinalAnswer.model_validate(structured)