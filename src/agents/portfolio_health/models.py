"""
Data models for the Portfolio Health agent.
Input: user profile + positions (from fixtures)
Output: structured health report
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------
# Input models (mirrors fixture shape)
# ---------------------------------------------------

class Position(BaseModel):
    ticker: str
    exchange: str
    quantity: float
    avg_cost: float
    currency: str
    purchased_at: str


class KYC(BaseModel):
    status: str


class Preferences(BaseModel):
    preferred_benchmark: str = "S&P 500"
    reporting_currency: str = "USD"
    income_focus: bool = False


class UserProfile(BaseModel):
    user_id: str
    name: str
    age: int
    country: str
    base_currency: str
    kyc: KYC
    risk_profile: Literal["conservative", "moderate", "aggressive"]
    positions: list[Position] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

# ---------------------------------------------------
# Output models
# ---------------------------------------------------

class ConcentrationRisk(BaseModel):
    top_position_pct: float
    top_3_positions_pct: float
    flag: Literal["low", "moderate", "high"]


class Performance(BaseModel):
    total_return_pct: float | None
    annualized_return_pct: float | None
    note: str = ""  # "based on avg cost vs current price"


class BenchmarkComparison(BaseModel):
    benchmark: str
    portfolio_return_pct: float | None
    benchmark_return_pct: float | None
    alpha_pct: float | None


class Observation(BaseModel):
    severity: Literal["info", "warning", "critical"]
    text: str


class PortfolioHealthReport(BaseModel):
    concentration_risk: ConcentrationRisk
    performance: Performance
    benchmark_comparison: BenchmarkComparison
    observations: list[Observation]
    disclaimer: str
    # surfaces for empty-portfolio BUILD guidance
    build_guidance: str | None = None