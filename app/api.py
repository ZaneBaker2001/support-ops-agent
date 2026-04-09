from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import ORJSONResponse

from app.config import get_settings
from app.logging_config import configure_logging
from app.schemas import AskRequest, FinalAnswer
from app.service import ask_agent

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting Support Ops Agent API")
    yield
    logger.info("Shutting down Support Ops Agent API")


app = FastAPI(
    title="Support Ops Agent API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/ask", response_model=FinalAnswer)
async def ask(request: AskRequest) -> FinalAnswer:
    try:
        return ask_agent(request.question)
    except Exception as exc:
        logger.exception("Agent invocation failed")
        message = str(exc).strip() or exc.__class__.__name__
        raise HTTPException(status_code=500, detail=message) from exc