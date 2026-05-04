from typing import TypedDict, Optional
from pydantic import BaseModel

class Output(BaseModel):
    agent: str
    intent: str
    entities: dict
    safety_verdict: str = "safe"

class ClassifierState(TypedDict):
    query: str
    prior_turns: list[str]
    messages: list[dict]
    raw_result: dict
    output: Output | None
    failed: bool

AGENTS = [
    "portfolio_health",
    "market_research",
    "investment_strategy",
    "financial_planning",
    "financial_calculator",
    "risk_assessment",
    "product_recommendation",
    "predictive_analysis",
    "customer_support",
    "general_query"
]

FALLBACK = Output(
    agent="general_query",
    intent="unknown",
    entities={},
    safety_verdict="safe",
)