from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", future=True)


@contextmanager
def db_session():
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def run_query(sql: str, params: dict | None = None) -> list[dict]:
    with db_session() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]