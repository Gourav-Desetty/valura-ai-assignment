"""
Portfolio Health Agent — main entrypoint.

Flow:
  1. Parse + validate user input (Pydantic)
  2. Fetch current prices and FX rates (yfinance)
  3. Run pure analytics (no LLM)
  4. Ask LLM for a plain-language narrative summary (one focused call)
  5. Assemble and return PortfolioHealthReport

The `llm` parameter accepts any callable with signature:
    llm(prompt: str) -> str
This makes it trivial to inject a mock in tests.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable

from .analytics import (
    compute_benchmark_comparison,
    compute_concentration,
    compute_performance,
    compute_position_values,
    generate_observations,
)
from .market import get_benchmark_return, get_current_prices, get_fx_rate
from .models import (
    Observation,
    PortfolioHealthReport,
    UserProfile,
)
from .narrative import build_narrative_prompt, parse_narrative

# logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is not investment advice. This report is for informational purposes only. "
    "Past performance is not indicative of future results. "
    "Please consult a qualified financial advisor before making investment decisions."
)

BUILD_GUIDANCE_TEMPLATE = (
    "Your account is verified and ready to invest. "
    "As a first step, consider your goals (retirement, growth, income), "
    "your timeline, and how much short-term volatility you can stomach. "
    "A simple starting point for a {risk_profile} investor is a low-cost "
    "diversified index fund — it gives you broad market exposure with minimal fees "
    "while you learn and build conviction."
)


def run(user_data: dict, llm: Callable[[str], str] | None = None) -> dict:
    """
    Run the Portfolio Health agent.

    Args:
        user_data: raw user dict (from fixture or API)
        llm: optional callable(prompt) -> str for narrative generation.
             If None, narrative is omitted gracefully.

    Returns:
        PortfolioHealthReport as a dict (JSON-serialisable).
    """
    # 1. Validate input
    user = UserProfile(**user_data)

    # 2. Empty portfolio — BUILD path
    if not user.positions:
        return _empty_portfolio_response(user)

    # 3. Fetch market data
    tickers = [p.ticker for p in user.positions]
    prices = get_current_prices(tickers)

    currencies = list({p.currency for p in user.positions})
    fx_rates = {c: get_fx_rate(c) for c in currencies}

    # 4. Analytics (pure, no I/O)
    pos_dicts = [p.model_dump() for p in user.positions]
    position_values = compute_position_values(pos_dicts, prices, fx_rates)
    concentration = compute_concentration(position_values)
    performance = compute_performance(pos_dicts, prices, fx_rates)

    benchmark_name = user.preferences.preferred_benchmark
    oldest_date = _oldest_purchase_date(user)
    benchmark_return = get_benchmark_return(benchmark_name, oldest_date) if oldest_date else None
    benchmark_comparison = compute_benchmark_comparison(
        performance.total_return_pct, benchmark_name, benchmark_return
    )

    observations = generate_observations(
        positions=pos_dicts,
        position_values=position_values,
        concentration=concentration,
        performance=performance,
        benchmark=benchmark_comparison,
        risk_profile=user.risk_profile,
        user_age=user.age,
        income_focus=user.preferences.income_focus,
    )

    # 5. Optional LLM narrative (non-blocking)
    narrative = _get_narrative(llm, user, position_values, concentration, performance, benchmark_comparison, observations)
    if narrative:
        observations.insert(0, Observation(severity="info", text=narrative))

    report = PortfolioHealthReport(
        concentration_risk=concentration,
        performance=performance,
        benchmark_comparison=benchmark_comparison,
        observations=observations,
        disclaimer=DISCLAIMER,
    )
    return report.model_dump()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_portfolio_response(user: UserProfile) -> dict:
    from .models import BenchmarkComparison, ConcentrationRisk, Performance, PortfolioHealthReport
    guidance = BUILD_GUIDANCE_TEMPLATE.format(risk_profile=user.risk_profile)
    report = PortfolioHealthReport(
        concentration_risk=ConcentrationRisk(top_position_pct=0, top_3_positions_pct=0, flag="low"),
        performance=Performance(total_return_pct=None, annualized_return_pct=None, note="No positions yet"),
        benchmark_comparison=BenchmarkComparison(
            benchmark=user.preferences.preferred_benchmark,
            portfolio_return_pct=None,
            benchmark_return_pct=None,
            alpha_pct=None,
        ),
        observations=[
            Observation(
                severity="info",
                text=(
                    f"Welcome, {user.name}! Your account is verified and ready. "
                    "You don't have any positions yet — see the guidance below to get started."
                ),
            )
        ],
        disclaimer=DISCLAIMER,
        build_guidance=guidance,
    )
    return report.model_dump()


def _oldest_purchase_date(user: UserProfile) -> str | None:
    from datetime import datetime
    dates = []
    for p in user.positions:
        try:
            dates.append(datetime.fromisoformat(p.purchased_at).date())
        except ValueError:
            pass
    return str(min(dates)) if dates else None


def _get_narrative(llm, user, position_values, concentration, performance, benchmark, observations) -> str | None:
    if llm is None:
        return None
    try:
        prompt = build_narrative_prompt(user, position_values, concentration, performance, benchmark, observations)
        raw = llm(prompt)
        return parse_narrative(raw)
    except Exception as exc:
        return None