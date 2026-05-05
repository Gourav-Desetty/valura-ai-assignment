"""
Pure analytics functions for the Portfolio Health agent.
No I/O, no LLM calls — just math on dicts.
Each function is independently testable.
"""
from __future__ import annotations
import math
from datetime import date, datetime
from .models import (
    BenchmarkComparison,
    ConcentrationRisk,
    Observation,
    Performance,
)

# Concentration thresholds
_CONC_HIGH = 40.0       
_CONC_MODERATE = 20.0  


def compute_position_values(
    positions: list[dict],
    prices: dict[str, float | None],
    fx_rates: dict[str, float],
) -> dict[str, float]:
    """
    Returns {ticker: current_value_in_reporting_currency}.
    Falls back to avg_cost * quantity when price is unavailable.
    """
    values: dict[str, float] = {}
    for pos in positions:
        ticker = pos["ticker"]
        price = prices.get(ticker)
        if price is None:
            # graceful degradation: use cost basis
            price = pos["avg_cost"]
        fx = fx_rates.get(pos["currency"], 1.0)
        values[ticker] = price * pos["quantity"] * fx
    return values


def compute_concentration(position_values: dict[str, float]) -> ConcentrationRisk:
    total = sum(position_values.values())
    if total == 0:
        return ConcentrationRisk(top_position_pct=0, top_3_positions_pct=0, flag="low")

    sorted_vals = sorted(position_values.values(), reverse=True)
    top1_pct = sorted_vals[0] / total * 100
    top3_pct = sum(sorted_vals[:3]) / total * 100

    if top1_pct >= _CONC_HIGH:
        flag = "high"
    elif top1_pct >= _CONC_MODERATE:
        flag = "moderate"
    else:
        flag = "low"

    return ConcentrationRisk(
        top_position_pct=round(top1_pct, 1),
        top_3_positions_pct=round(top3_pct, 1),
        flag=flag,
    )


def compute_performance(
    positions: list[dict],
    prices: dict[str, float | None],
    fx_rates: dict[str, float],
) -> Performance:
    """
    Simple cost-basis vs current-price performance.
    Annualises using the oldest purchased_at date in the portfolio.
    """
    if not positions:
        return Performance(
            total_return_pct=None,
            annualized_return_pct=None,
            note="No positions",
        )

    total_cost = 0.0
    total_current = 0.0
    oldest_date: date | None = None

    for pos in positions:
        fx = fx_rates.get(pos["currency"], 1.0)
        cost = pos["avg_cost"] * pos["quantity"] * fx
        price = prices.get(pos["ticker"]) or pos["avg_cost"]
        current = price * pos["quantity"] * fx

        total_cost += cost
        total_current += current

        try:
            pd = datetime.fromisoformat(pos["purchased_at"]).date()
            if oldest_date is None or pd < oldest_date:
                oldest_date = pd
        except (ValueError, KeyError):
            pass

    if total_cost == 0:
        return Performance(total_return_pct=None, annualized_return_pct=None)

    total_return_pct = (total_current - total_cost) / total_cost * 100

    annualized: float | None = None
    if oldest_date:
        years = (date.today() - oldest_date).days / 365.25
        if years > 0.08:  # at least ~1 month to avoid nonsense annualisation
            try:
                ratio = total_current / total_cost
                annualized = (ratio ** (1 / years) - 1) * 100
            except (ZeroDivisionError, ValueError):
                pass

    return Performance(
        total_return_pct=round(total_return_pct, 2),
        annualized_return_pct=round(annualized, 2) if annualized is not None else None,
        note="Based on avg cost vs current market price",
    )


def compute_benchmark_comparison(
    portfolio_return_pct: float | None,
    benchmark_name: str,
    benchmark_return_pct: float | None,
) -> BenchmarkComparison:
    alpha: float | None = None
    if portfolio_return_pct is not None and benchmark_return_pct is not None:
        alpha = round(portfolio_return_pct - benchmark_return_pct, 2)

    return BenchmarkComparison(
        benchmark=benchmark_name,
        portfolio_return_pct=portfolio_return_pct,
        benchmark_return_pct=benchmark_return_pct,
        alpha_pct=alpha,
    )


def generate_observations(
    positions: list[dict],
    position_values: dict[str, float],
    concentration: ConcentrationRisk,
    performance: Performance,
    benchmark: BenchmarkComparison,
    risk_profile: str,
    user_age: int,
    income_focus: bool,
) -> list[Observation]:
    """
    Rule-based observation generator.
    Produces the 2-4 most important observations — no noise.
    """
    obs: list[Observation] = []
    total = sum(position_values.values())

    # 1. Concentration warning
    if concentration.flag == "high":
        top_ticker = max(position_values, key=position_values.__getitem__)
        obs.append(Observation(
            severity="warning",
            text=(
                f"{top_ticker} makes up {concentration.top_position_pct}% of your portfolio. "
                "That's heavily concentrated in a single stock — a sharp move there "
                "would have an outsized effect on your overall wealth."
            ),
        ))
    elif concentration.flag == "moderate":
        top_ticker = max(position_values, key=position_values.__getitem__)
        obs.append(Observation(
            severity="info",
            text=(
                f"{top_ticker} is your largest position at {concentration.top_position_pct}%. "
                "Worth keeping an eye on as the portfolio grows."
            ),
        ))

    # 2. Performance vs benchmark
    if benchmark.alpha_pct is not None:
        if benchmark.alpha_pct > 0:
            obs.append(Observation(
                severity="info",
                text=(
                    f"You're outperforming {benchmark.benchmark} by "
                    f"{benchmark.alpha_pct}% over this period — good result."
                ),
            ))
        else:
            obs.append(Observation(
                severity="info",
                text=(
                    f"You're trailing {benchmark.benchmark} by "
                    f"{abs(benchmark.alpha_pct)}%. "
                    "A low-cost index fund might be worth considering for part of your allocation."
                ),
            ))

    # 3. Age / risk mismatch
    if user_age >= 60 and risk_profile == "aggressive":
        obs.append(Observation(
            severity="warning",
            text=(
                "Your risk profile is set to aggressive, but at 60+ "
                "most advisors recommend shifting some allocation toward bonds or "
                "income-generating assets to reduce drawdown risk."
            ),
        ))

    # 4. Sector concentration (tech-heavy check)
    tech_tickers = {"AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA", "AMD", "QQQ", "ASML", "ASML.AS"}
    tech_value = sum(v for t, v in position_values.items() if t.upper() in tech_tickers)
    if total > 0 and tech_value / total > 0.6:
        obs.append(Observation(
            severity="info",
            text=(
                f"Over {round(tech_value / total * 100)}% of your portfolio is in technology. "
                "Tech tends to be volatile — consider whether broader sector exposure fits your goals."
            ),
        ))

    # 5. Income-focused retiree: check for growth-heavy allocation
    if income_focus:
        income_tickers = {"JNJ", "PG", "KO", "VYM", "SCHD", "BND", "TLT"}
        income_value = sum(v for t, v in position_values.items() if t.upper() in income_tickers)
        if total > 0 and income_value / total < 0.5:
            obs.append(Observation(
                severity="info",
                text=(
                    "Your income-generating holdings are below 50% of the portfolio. "
                    "Given your income focus, you may want to review the balance between "
                    "growth assets and dividend/bond holdings."
                ),
            ))

    # 6. Single-position portfolio
    if len(positions) == 1:
        obs.append(Observation(
            severity="warning",
            text=(
                "You only hold one position. Consider spreading across at least "
                "5-10 uncorrelated holdings to reduce single-stock risk."
            ),
        ))

    # Cap at 4 to avoid noise; prioritise warnings first
    obs.sort(key=lambda o: 0 if o.severity == "warning" else 1)
    return obs[:4]