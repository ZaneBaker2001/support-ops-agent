from __future__ import annotations

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.config import get_settings
from app.schemas import FinalAnswer
from app.tools import all_tools


SYSTEM_PROMPT = """
You are SupportOpsAgent, an AI copilot for a SaaS support operations team.

Your job:
- Investigate support issues using the available tools.
- Prefer tool-grounded answers over intuition.
- Be concise, analytical, and operationally useful.
- When evidence is thin, say so explicitly.
- Never invent policies, outages, or internal facts.
- Return a structured response that can be consumed by an API client.

Reasoning policy:
- For operational questions, inspect both docs and ticket data when relevant.
- If the prompt suggests a spike, compare trends using data tools.
- If recommending action, prioritize low-regret steps and owner clarity.
"""


def build_agent():
    settings = get_settings()

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set USE_MOCK_LLM=true for local demo mode, or provide a real API key."
        )

    llm = init_chat_model(
        model=settings.openai_model,
        model_provider="openai",
        api_key=settings.openai_api_key,
        temperature=0,
    )

    return create_agent(
        model=llm,
        tools=all_tools(),
        system_prompt=SYSTEM_PROMPT,
        response_format=FinalAnswer,
    )