from __future__ import annotations

import json
import logging
from typing import Any

from langchain.tools import tool

from app.db import run_query
from app.knowledge import get_knowledge_base

logger = logging.getLogger(__name__)


@tool
def retrieve_support_docs(query: str) -> str:
    """
    Search internal support runbooks, postmortems, and troubleshooting docs.
    Use this when the user asks about causes, policies, fixes, or standard procedures.
    """
    kb = get_knowledge_base()
    hits = kb.search(query, k=4)
    if not hits:
        return "No relevant internal docs were found."

    payload = [
        {"source": hit.source, "snippet": hit.text[:700]}
        for hit in hits
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def ticket_volume_by_category(days: int = 7) -> str:
    """
    Return ticket counts by category over the last N days.
    Useful for identifying spikes or trending issue areas.
    """
    sql = """
    SELECT
      category,
      COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= datetime('now', :window)
    GROUP BY category
    ORDER BY ticket_count DESC
    """
    rows = run_query(sql, {"window": f"-{days} day"})
    return json.dumps(rows, ensure_ascii=False, indent=2)


@tool
def incidents_for_keyword(keyword: str, days: int = 30) -> str:
    """
    Search recent tickets by keyword in title or description.
    Useful for grounding hypotheses in recent operational data.
    """
    sql = """
    SELECT
      id,
      created_at,
      category,
      priority,
      title,
      status
    FROM tickets
    WHERE created_at >= datetime('now', :window)
      AND (
        lower(title) LIKE lower(:pattern)
        OR lower(description) LIKE lower(:pattern)
      )
    ORDER BY created_at DESC
    LIMIT 20
    """
    rows = run_query(sql, {"window": f"-{days} day", "pattern": f"%{keyword}%"})
    return json.dumps(rows, ensure_ascii=False, indent=2)


@tool
def top_unresolved_tickets(limit: int = 10) -> str:
    """
    Return the highest-priority unresolved tickets.
    Useful when recommending human follow-up or escalation.
    """
    sql = """
    SELECT
      id,
      created_at,
      category,
      priority,
      title,
      owner,
      status
    FROM tickets
    WHERE status NOT IN ('resolved', 'closed')
    ORDER BY
      CASE priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        ELSE 4
      END,
      datetime(created_at) DESC
    LIMIT :limit
    """
    rows = run_query(sql, {"limit": limit})
    return json.dumps(rows, ensure_ascii=False, indent=2)


def all_tools() -> list[Any]:
    return [
        retrieve_support_docs,
        ticket_volume_by_category,
        incidents_for_keyword,
        top_unresolved_tickets,
    ]