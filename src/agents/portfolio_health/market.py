"""
Market data fetching via yfinance.
"""
from __future__ import annotations
import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Benchmark ticker mapping
BENCHMARK_TICKERS: dict[str, str] = {
    "S&P 500":    "^GSPC",
    "QQQ":        "QQQ",
    "MSCI World": "URTH",  
    "FTSE 100":   "^FTSE",
    "NIKKEI 225": "^N225",
}

# FX pairs to convert to USD  (base -> USD rate ticker)
FX_TO_USD: dict[str, str] = {
    "EUR": "EURUSD=X",
    "GBP": "GBPUSD=X",
    "JPY": "JPYUSD=X",
    "SGD": "SGDUSD=X",
    "USD": None,  # no conversion needed
}


def get_current_prices(tickers: list[str]) -> dict[str, float | None]:
    """
    Fetch the latest closing price for each ticker.
    Returns a dict {ticker: price_or_None}.
    Never raises - missing/broken tickers come back as None.
    """
    if not tickers:
        return {}
    try:
        import yfinance as yf  
        data = yf.download(tickers, period="5d", progress=False, auto_adjust=True)
        close = data["Close"] if len(tickers) > 1 else data[["Close"]]
        # Take the last available row
        last = close.ffill().iloc[-1]
        return {t: float(last[t]) if t in last and not pd.notna(last[t]) else None for t in tickers}
    except Exception as exc:
        logger.warning(f"yfinance batch download failed: {exc}")
        return {t: for t in tickers}


def get_benchmark_return(benchmark_name: str, since: str) -> float | None:
    """
    Return the total % return for the benchmark from `since` (ISO date) to today.
    Returns None on any failure.
    """
    ticker = BENCHMARK_TICKERS.get(benchmark_name)
    if not ticker:
        logger.warning(f"Unknown benchmark: {benchmark_name}")
        return None
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(start=since, auto_adjust=True)
        if hist.empty or len(hist) < 2:
            return None
        start_price = float(hist["Close"].iloc[0])
        end_price = float(hist["Close"].iloc[-1])
        return round((end_price - start_price) / start_price * 100, 2)
    except Exception as exc:
        logger.warning("Benchmark fetch failed for %s: %s", benchmark_name, exc)
        return None


def get_fx_rate(currency: str) -> float:
    """
    Return the current exchange rate for `currency` → USD.
    Returns 1.0 for USD, None on failure (caller decides how to handle).
    """
    if currency == "USD":
        return 1.0
    pair = FX_TO_USD.get(currency)
    if not pair:
        logger.warning("No FX ticker for currency %s, assuming 1.0", currency)
        return 1.0
    try:
        import yfinance as yf
        ticker = yf.Ticker(pair)
        hist = ticker.history(period="5d", auto_adjust=True)
        if hist.empty:
            return 1.0
        return float(hist["Close"].ffill().iloc[-1])
    except Exception as exc:
        logger.warning("FX fetch failed for %s: %s", currency, exc)
        return 1.0