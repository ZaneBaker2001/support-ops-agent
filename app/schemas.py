from typing import Literal, List
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=4000)
    conversation_id: str | None = None


class Evidence(BaseModel):
    source: str
    snippet: str


class FinalAnswer(BaseModel):
    summary: str = Field(description="Executive summary for a support lead.")
    severity: Literal["low", "medium", "high", "critical"]
    likely_root_causes: List[str]
    recommended_actions: List[str]
    evidence: List[Evidence]
    needs_human_followup: bool