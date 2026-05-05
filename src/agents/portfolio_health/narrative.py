"""
LLM narrative helpers for the Portfolio Health agent.
"""

def build_narrative_prompt(
    user,
    position_values: dict[str, float],
    concentration,
    performance,
    benchmark,
    observations) -> str:

    total = sum(position_values.values())
    top_holdings = sorted(position_values.items(), key=lambda x: x[1], reverse=True)[:3]
    top_str = ", ".join(f"{t} ({v / total * 100:.1f}%)" for t, v in top_holdings)

    obs_text = "\n".join(f"- [{o.severity.upper()}] {o.text}" for o in observations)

    perf_str = (
        f"{performance.total_return_pct:.1f}% total return"
        if performance.total_return_pct is not None
        else "performance data unavailable"
    )

    bench_str = (
        f"vs {benchmark.benchmark} at {benchmark.benchmark_return_pct:.1f}% "
        f"(alpha: {benchmark.alpha_pct:+.1f}%)"
        if benchmark.alpha_pct is not None
        else ""
    )

    return f"""You are a plain-language financial health coach for a novice investor.

User: {user.name}, age {user.age}, {user.risk_profile} risk profile.
Portfolio total (approx): ${total:,.0f}
Top 3 holdings: {top_str}
Performance: {perf_str} {bench_str}

Key observations already identified:
{obs_text}

Write 1–2 plain English sentences that give this specific user the single most important takeaway from their portfolio health check. 
Be direct and human — no jargon, no bullet points, no greeting. Do not repeat the numbers verbatim."""


def parse_narrative(raw) -> str:
    """
    Clean up the LLM response — strip whitespace, truncate if absurdly long.
    Accepts any type; returns empty string if not usable.
    """
    if not isinstance(raw, str) or not raw:
        return ""
    cleaned = raw.strip().strip('"').strip("'")
    # Hard cap — if the LLM rambled, we cut it
    if len(cleaned) > 400:
        cleaned = cleaned[:397] + "..."
    return cleaned