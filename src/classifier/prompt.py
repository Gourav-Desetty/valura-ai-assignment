PROMPT = """
Given a user query, return ONLY a JSON object with these fields:
- agent: one of [portfolio_health, market_research, investment_strategy,
  financial_planning, financial_calculator, risk_assessment,
  product_recommendation, predictive_analysis, customer_support, general_query]
- intent: short description of what the user wants
- entities: extracted values from the query
- safety_verdict: "safe" or "review"

Entity rules:
- tickers: uppercase array e.g. ["AAPL", "NVDA"]
- amount: number only e.g. 5000
- rate: decimal e.g. 0.08 for 8%
- period_years: integer
- frequency: one of [daily, weekly, monthly, yearly]
- horizon: one of [6_months, 1_year, 5_years]
- time_period: one of [today, this_week, this_month, this_year]
- index: one of [S&P 500, FTSE 100, NIKKEI 225, MSCI World]
- action: one of [buy, sell, hold, hedge, rebalance]
- goal: one of [retirement, education, house, FIRE, emergency_fund]
- topics: array of strings
- sectors: array of strings
- currency: ISO 4217 e.g. USD, EUR, GBP

Follow-up rules:
- If the query references "it", "they", "that", "this" or is very short,
  use prior turns to resolve what the user is referring to
- Carry the ticker/topic from prior turn if current query has none

Return only valid JSON. No explanation. No markdown.
"""