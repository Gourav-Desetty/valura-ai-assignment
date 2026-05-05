from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

from src.safety import check as safety_check
from src.classifier.classifier import classify
from src.agents.portfolio_health import run as run_portfolio_health

logger = logging.getLogger(__name__)

router = APIRouter()

PIPELINE_TIMEOUT = 25
CLASSIFIER_TIMEOUT = 8


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class UserQuery(BaseModel):
    query: str
    user: dict[str, Any] = Field(default_factory=dict)
    prior_turns: list[str] = Field(default_factory=list)
    session_id: str | None = None


# -------------------------------------------------------
# Agent dispatch
# -------------------------------------------------------

def _dispatch(agent: str, user: dict, intent: str, entities: dict) -> dict:
    if agent == "portfolio_health":
        return run_portfolio_health(user)

    # Stub for every other agent in the taxonomy
    return {
        "type": "not_implemented",
        "agent": agent,
        "intent": intent,
        "entities": entities,
        "message": f"The '{agent}' agent is not implemented in this build.",
        "disclaimer": "This is not investment advice.",
    }


# ---------------------------------------------------------------------------
# SSE event helpers
# ---------------------------------------------------------------------------

def _event(name: str, data: dict) -> dict:
    return {"event": name, "data": json.dumps(data)}


# ----------------------------------------------------------------
# Pipeline generator
# ----------------------------------------------------------------

async def _pipeline(req: UserQuery) -> AsyncGenerator[dict, None]:
    # 1. Safety guard — sync, no LLM, must be fast
    verdict = safety_check(req.query)
    if verdict.blocked:
        yield _event("safety_blocked", {
            "category": verdict.category,
            "message": verdict.message,
        })
        yield _event("done", {"status": "blocked"})
        return

    # 2. Classify — one LLM call with its own timeout
    yield _event("metadata", {"status": "classifying"})
    try:
        classification = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: classify(req.query, prior_turns=req.prior_turns)
            ),
            timeout=CLASSIFIER_TIMEOUT,
        )
    except asyncio.TimeoutError:
        yield _event("error", {"type": "classifier_timeout", "message": "Classification timed out."})
        yield _event("done", {"status": "error"})
        return
    except Exception as exc:
        logger.exception("Classifier error: %s", exc)
        yield _event("error", {"type": "classifier_error", "message": "Could not classify your query."})
        yield _event("done", {"status": "error"})
        return

    yield _event("classification", {
        "intent": classification.intent,
        "agent": classification.agent,
        "entities": classification.entities,
        "safety_verdict": classification.safety_verdict, 
    })

    # 3. Agent — remaining budget
    try:
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _dispatch(
                    classification.agent,
                    req.user,
                    classification.intent,
                    classification.entities,
                ),
            ),
            timeout=PIPELINE_TIMEOUT - CLASSIFIER_TIMEOUT,
        )
    except asyncio.TimeoutError:
        yield _event("error", {"type": "agent_timeout", "message": "Agent timed out."})
        yield _event("done", {"status": "error"})
        return
    except Exception as exc:
        logger.exception("Agent error: %s", exc)
        yield _event("error", {"type": "agent_error", "message": "Agent failed to process your request."})
        yield _event("done", {"status": "error"})
        return

    yield _event("agent_result", result)
    yield _event("done", {"status": "complete"})


# ---------------------------------------------------------------------------
# Endpoint
# -------------------------------------------------------------------------

@router.post("/query")
async def query(req: UserQuery):
    """
    Streams the full pipeline response as SSE.

    Events emitted (in order):
      metadata        — pipeline started / classifying
      safety_blocked  — if safety guard fires (followed by done)
      classification  — intent, agent, entities, safety_verdict
      agent_result    — structured agent output (or stub)
      done            — always the last event; status = complete | blocked | error
      error           — on any pipeline failure (always followed by done)
    """
    return EventSourceResponse(_pipeline(req))