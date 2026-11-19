"""FastAPI endpoints and production static-file serving for the React UI."""
from __future__ import annotations

import logging
import math
from pathlib import Path
import re
import threading
import time
from datetime import date, datetime, timezone
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yfinance as yf
from backend import market_radar, wheel

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = (REPO_ROOT / "docs").resolve()
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
INDEX_FILE = FRONTEND_DIST / "index.html"
logger = logging.getLogger(__name__)
_CACHE: dict[tuple[Any, ...], tuple[float, Any]] = {}
_CACHE_LOCK = threading.Lock()

POPULAR_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "GOOGL", "name": "Alphabet Inc. (Class A)"},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc. (Class B)"},
    {"symbol": "AVGO", "name": "Broadcom Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "LLY", "name": "Eli Lilly and Company"},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "WMT", "name": "Walmart Inc."},
    {"symbol": "ORCL", "name": "Oracle Corporation"},
    {"symbol": "NFLX", "name": "Netflix, Inc."},
    {"symbol": "COST", "name": "Costco Wholesale Corporation"},
    {"symbol": "MA", "name": "Mastercard Incorporated"},
    {"symbol": "AMD", "name": "Advanced Micro Devices, Inc."},
    {"symbol": "KO", "name": "The Coca-Cola Company"},
    {"symbol": "DIS", "name": "The Walt Disney Company"},
    {"symbol": "PLTR", "name": "Palantir Technologies Inc."},
    {"symbol": "INTC", "name": "Intel Corporation"},
    {"symbol": "XOM", "name": "Exxon Mobil Corporation"},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
]

EARNINGS_WATCHLIST = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "PGR", "name": "The Progressive Corporation"},
    {"symbol": "QCOM", "name": "Qualcomm Incorporated"},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "BAC", "name": "Bank of America Corporation"},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "AVGO", "name": "Broadcom Inc."},
    {"symbol": "ORCL", "name": "Oracle Corporation"},
    {"symbol": "AMD", "name": "Advanced Micro Devices, Inc."},
    {"symbol": "INTC", "name": "Intel Corporation"},
    {"symbol": "NFLX", "name": "Netflix, Inc."},
    {"symbol": "ADBE", "name": "Adobe Inc."},
    {"symbol": "CRM", "name": "Salesforce, Inc."},
    {"symbol": "IBM", "name": "International Business Machines"},
    {"symbol": "TXN", "name": "Texas Instruments Incorporated"},
]

LOOKBACKS = {
    "1D": ("1d", ("1m", "5m", "15m", "30m", "1h")),
    "1W": ("5d", ("1m", "5m", "15m", "30m", "1h")),
    "1M": ("1mo", ("30m", "1h", "1d")),
    "3M": ("3mo", ("1d",)),
    "6M": ("6mo", ("1d",)),
    "1Y": ("1y", ("1d", "1wk")),
    "5Y": ("5y", ("1wk", "1mo")),
    "MAX": ("max", ("1mo",)),
}

app = FastAPI(
    title="Fun Embedded Systems Docs API",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


def _document_files() -> list[Path]:
    paths = []
    for path in DOCS_ROOT.rglob("*.md"):
        relative = path.relative_to(DOCS_ROOT)
        if any(part.startswith(".") for part in relative.parts):
            continue
        resolved = path.resolve()
        if resolved.is_file() and resolved.is_relative_to(DOCS_ROOT):
            paths.append(resolved)
    return sorted(paths, key=lambda item: item.relative_to(DOCS_ROOT).as_posix().casefold())


def _title_for(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = line.strip()
        if heading.startswith("# "):
            return heading[2:].strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def _frontend_index() -> FileResponse:
    if not INDEX_FILE.is_file():
        raise HTTPException(
            status_code=503,
            detail="Frontend build is missing. From the repository root, run ./install.sh.",
        )
    return FileResponse(INDEX_FILE)


def _cached(key: tuple[Any, ...], ttl: int, loader: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _CACHE_LOCK:
        saved = _CACHE.get(key)
        if saved and saved[0] > now:
            return saved[1]
    value = loader()
    with _CACHE_LOCK:
        _CACHE[key] = (now + ttl, value)
    return value


def _symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.-]{1,15}", symbol):
        raise HTTPException(status_code=422, detail="Enter a valid ticker symbol.")
    return symbol


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _safe_dict_get(source: Any, key: str) -> Any:
    try:
        return source.get(key)
    except (AttributeError, TypeError):
        return None


def _statement_frame(ticker: yf.Ticker, statement: str, frequency: str) -> Any:
    attribute = {
        "income": "financials",
        "balance": "balance_sheet",
        "cashflow": "cashflow",
    }[statement]
    if frequency == "quarterly":
        attribute = f"quarterly_{attribute}"
    return getattr(ticker, attribute)


def _statement_payload(frame: Any) -> dict[str, Any]:
    if frame is None or getattr(frame, "empty", True):
        return {"periods": [], "rows": []}
    columns = list(frame.columns)[:8]
    periods = [column.strftime("%Y-%m-%d") if hasattr(column, "strftime") else str(column) for column in columns]
    rows = []
    for label, series in frame.iterrows():
        values = []
        for column in columns:
            values.append(_number(series[column]))
        if any(value is not None for value in values):
            rows.append({"label": str(label), "values": values})
    return {"periods": periods, "rows": rows[:60]}


@app.get("/api/market/search")
def search_stocks(q: str = "") -> list[dict[str, str]]:
    query = q.strip().casefold()
    matches = [stock for stock in POPULAR_STOCKS if not query or query in stock["symbol"].casefold() or query in stock["name"].casefold()]
    if query:
        direct = q.strip().upper()
        if re.fullmatch(r"[A-Z0-9.-]{1,15}", direct) and not any(stock["symbol"] == direct for stock in matches):
            matches.insert(0, {"symbol": direct, "name": "Look up ticker"})
    return matches[:12]


def _next_earnings_date(symbol: str) -> str | None:
    """Return the next date in Yahoo Finance's calendar, if one is listed."""
    calendar = yf.Ticker(symbol).calendar
    if not calendar:
        return None
    dates = calendar.get("Earnings Date") if isinstance(calendar, dict) else None
    if dates is None:
        return None
    if not isinstance(dates, (list, tuple)):
        dates = [dates]
    today = time.strftime("%Y-%m-%d", time.gmtime())
    normalized = []
    for value in dates:
        try:
            date = value.date() if hasattr(value, "date") else value
            date_string = date.isoformat()[:10]
            if date_string >= today:
                normalized.append(date_string)
        except (AttributeError, TypeError, ValueError):
            continue
    return min(normalized) if normalized else None


@app.get("/api/market/earnings")
def earnings_calendar(symbols: str = "") -> list[dict[str, Any]]:
    """List upcoming earnings dates for the curated watchlist and requested ticker."""
    requested = [_symbol(value) for value in symbols.split(",") if value.strip()]
    stocks = list(EARNINGS_WATCHLIST)
    known = {stock["symbol"] for stock in stocks}
    stocks.extend({"symbol": symbol, "name": symbol} for symbol in requested if symbol not in known)

    def load() -> list[dict[str, Any]]:
        results = []
        for stock in stocks:
            symbol = stock["symbol"]
            try:
                date = _next_earnings_date(symbol)
            except Exception as error:
                logger.info("Earnings calendar unavailable for %s: %s", symbol, error)
                date = None
            results.append({**stock, "date": date})
        return results

    # Keep refreshes bounded while avoiding a burst of Yahoo requests on every view.
    return _cached(("earnings", tuple(stock["symbol"] for stock in stocks)), 21600, load)


def _option_contracts(frame: Any) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    contracts = []
    for _, row in frame.iterrows():
        bid = _number(row.get("bid"))
        ask = _number(row.get("ask"))
        contracts.append({
            "contractSymbol": str(row.get("contractSymbol") or ""),
            "strike": _number(row.get("strike")),
            "bid": bid,
            "ask": ask,
            "mark": (bid + ask) / 2 if bid is not None and ask is not None and bid > 0 and ask > 0 else _number(row.get("lastPrice")),
            "lastPrice": _number(row.get("lastPrice")),
            "impliedVolatility": _number(row.get("impliedVolatility")),
            "volume": _number(row.get("volume")),
            "openInterest": _number(row.get("openInterest")),
        })
    return [contract for contract in contracts if contract["strike"] is not None]


@app.get("/api/options/{symbol}")
def option_chain(symbol: str, expiration: str = "") -> dict[str, Any]:
    symbol = _symbol(symbol)

    def load() -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        expirations = list(ticker.options or ())
        if expiration and expiration not in expirations:
            raise HTTPException(status_code=422, detail="Choose an expiration returned by the options data source.")
        selected = expiration or (expirations[0] if expirations else "")
        calls: list[dict[str, Any]] = []
        puts: list[dict[str, Any]] = []
        if selected:
            chain = ticker.option_chain(selected)
            calls = _option_contracts(chain.calls)
            puts = _option_contracts(chain.puts)
        try:
            fast_info = dict(ticker.fast_info)
        except Exception:
            fast_info = {}
        price = _number(_safe_dict_get(fast_info, "last_price"))
        if price is None:
            history = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if history is not None and not history.empty:
                price = _number(history["Close"].dropna().iloc[-1])
        return {"symbol": symbol, "underlyingPrice": price, "expirations": expirations, "expiration": selected or None,
                "calls": calls, "puts": puts, "source": "Yahoo Finance via yfinance"}

    try:
        return _cached(("options", symbol, expiration), 90, load)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Options data request failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Options data is unavailable from the market data source.") from error


def _normal_cdf(value: float) -> float:
    return (1 + math.erf(value / math.sqrt(2))) / 2


def _model_greeks(side: str, spot: float, strike: float, years: float, volatility: float,
                  risk_free_rate: float, dividend_yield: float) -> dict[str, float] | None:
    """European Black-Scholes Greeks, expressed per share and with explicit assumptions."""
    if min(spot, strike, years, volatility) <= 0:
        return None
    root_time = math.sqrt(years)
    sigma_root = volatility * root_time
    d1 = (math.log(spot / strike) + (risk_free_rate - dividend_yield + volatility * volatility / 2) * years) / sigma_root
    d2 = d1 - sigma_root
    discount_r = math.exp(-risk_free_rate * years)
    discount_q = math.exp(-dividend_yield * years)
    density = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    if side == "CALL":
        delta = discount_q * _normal_cdf(d1)
        theta = (-spot * discount_q * density * volatility / (2 * root_time)
                 - risk_free_rate * strike * discount_r * _normal_cdf(d2)
                 + dividend_yield * spot * discount_q * _normal_cdf(d1)) / 365
        rho = strike * years * discount_r * _normal_cdf(d2) / 100
    else:
        delta = discount_q * (_normal_cdf(d1) - 1)
        theta = (-spot * discount_q * density * volatility / (2 * root_time)
                 + risk_free_rate * strike * discount_r * _normal_cdf(-d2)
                 - dividend_yield * spot * discount_q * _normal_cdf(-d1)) / 365
        rho = -strike * years * discount_r * _normal_cdf(-d2) / 100
    gamma = discount_q * density / (spot * sigma_root)
    vega = spot * discount_q * density * root_time / 100
    return {"delta": delta, "gamma": gamma, "thetaPerDay": theta,
            "vegaPerVolPoint": vega, "rhoPerRatePoint": rho}


def _treasury_proxy() -> dict[str, Any]:
    def load() -> dict[str, Any]:
        try:
            frame = yf.Ticker("^IRX").history(period="10d", interval="1d", auto_adjust=False)
            if frame is not None and not frame.empty:
                rate = _number(frame["Close"].dropna().iloc[-1])
                stamp = frame.index[-1]
                return {"ratePct": rate, "asOf": stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10]}
        except Exception as error:
            logger.info("Treasury yield proxy unavailable: %s", error)
        return {"ratePct": None, "asOf": None}
    return _cached(("options_research_treasury_proxy",), 3600, load)


def _historical_strike_stats(closes: list[float], highs: list[float], lows: list[float],
                             strike_ratio: float, sessions: int, side: str) -> dict[str, Any]:
    returns: list[float] = []
    moves_toward_strike: list[float] = []
    touched = finished_itm = 0
    for start in range(max(0, len(closes) - sessions)):
        end = start + sessions
        base = closes[start]
        if base <= 0 or end >= len(closes):
            continue
        barrier = base * strike_ratio
        path_high = max(highs[start + 1:end + 1])
        path_low = min(lows[start + 1:end + 1])
        close_return = closes[end] / base - 1
        returns.append(close_return * 100)
        if side == "PUT":
            touched += path_low <= barrier
            finished_itm += closes[end] <= barrier
            moves_toward_strike.append((path_low / base - 1) * 100)
        else:
            touched += path_high >= barrier
            finished_itm += closes[end] >= barrier
            moves_toward_strike.append((path_high / base - 1) * 100)
    count = len(returns)
    if not count:
        return {"windows": 0, "touchRate": None, "finishInMoneyRate": None,
                "averageMoveTowardStrikePct": None, "worstMoveTowardStrikePct": None}
    return {
        "windows": count,
        "touchRate": touched / count,
        "finishInMoneyRate": finished_itm / count,
        "averageMoveTowardStrikePct": sum(moves_toward_strike) / count,
        "worstMoveTowardStrikePct": min(moves_toward_strike) if side == "PUT" else max(moves_toward_strike),
        "averageHorizonReturnPct": sum(returns) / count,
        "minimumHorizonReturnPct": min(returns),
        "maximumHorizonReturnPct": max(returns),
    }


def _realized_volatility_pct(closes: list[float], periods: int) -> float | None:
    prices = closes[-(periods + 1):]
    returns = [math.log(prices[index] / prices[index - 1]) for index in range(1, len(prices)) if prices[index] > 0 and prices[index - 1] > 0]
    if len(returns) < 3:
        return None
    average = sum(returns) / len(returns)
    variance = sum((value - average) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance * 252) * 100


@app.get("/api/options/{symbol}/research")
def option_contract_research(symbol: str, expiration: str, option_type: str = "PUT", lookback: str = "5y") -> dict[str, Any]:
    symbol = _symbol(symbol)
    option_type = option_type.upper()
    if option_type not in {"PUT", "CALL"}:
        raise HTTPException(status_code=422, detail="Option type must be PUT or CALL.")
    if lookback not in {"1y", "2y", "5y", "10y"}:
        raise HTTPException(status_code=422, detail="Lookback must be 1y, 2y, 5y, or 10y.")
    try:
        expiry_date = date.fromisoformat(expiration)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Expiration must be YYYY-MM-DD.") from error
    days_to_expiration = max(0, (expiry_date - date.today()).days)
    if days_to_expiration < 1:
        raise HTTPException(status_code=422, detail="Choose a future expiration date.")

    def load() -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        if expiration not in list(ticker.options or ()):
            raise HTTPException(status_code=422, detail="Choose an expiration returned by the options data source.")
        chain = ticker.option_chain(expiration)
        frame = chain.puts if option_type == "PUT" else chain.calls
        contracts = _option_contracts(frame)
        def load_history() -> Any:
            frame = ticker.history(period=lookback, interval="1d", auto_adjust=False, actions=False)
            if frame is None or frame.empty:
                raise HTTPException(status_code=502, detail="Historical daily prices are unavailable for this ticker.")
            return frame

        history = _cached(("options_research_history", symbol, lookback), 21600, load_history)
        if history is None or history.empty:
            raise HTTPException(status_code=502, detail="Historical daily prices are unavailable for this ticker.")
        valid_history = history.dropna(subset=["Close", "High", "Low"])
        close_values = [float(value) for value in valid_history["Close"].tolist()]
        high_values = [float(value) for value in valid_history["High"].tolist()]
        low_values = [float(value) for value in valid_history["Low"].tolist()]
        try:
            fast_info = dict(ticker.fast_info)
        except Exception:
            fast_info = {}
        spot = _number(_safe_dict_get(fast_info, "last_price")) or (close_values[-1] if close_values else None)
        if spot is None or not close_values:
            raise HTTPException(status_code=502, detail="Underlying price is unavailable.")
        sessions = max(1, round(days_to_expiration * 252 / 365))
        hv20 = _realized_volatility_pct(close_values, 20)
        hv60 = _realized_volatility_pct(close_values, 60)
        historical_expected_move = hv20 * math.sqrt(days_to_expiration / 365) if hv20 is not None else None
        windows = max(0, len(close_values) - sessions)
        avg_return = min_return = max_return = None
        if windows:
            horizon_returns = [((close_values[index + sessions] / close_values[index]) - 1) * 100 for index in range(windows) if close_values[index] > 0]
            if horizon_returns:
                avg_return = sum(horizon_returns) / len(horizon_returns)
                min_return, max_return = min(horizon_returns), max(horizon_returns)
        treasury = _treasury_proxy()
        rate = treasury["ratePct"]
        rate_decimal = rate / 100 if rate is not None else None
        try:
            dividend_series = _cached(("options_research_dividends", symbol), 3600, lambda: ticker.dividends)
            cutoff = date.today().toordinal() - 365
            trailing_dividends = sum(float(amount) for stamp, amount in dividend_series.items()
                                     if (stamp.date() if hasattr(stamp, "date") else stamp).toordinal() >= cutoff) if dividend_series is not None else 0
        except Exception:
            trailing_dividends = 0
        dividend_yield = max(0, trailing_dividends / spot) if spot > 0 else 0
        years = max(days_to_expiration / 365, 1 / 365)
        output = []
        for contract in contracts:
            strike = contract["strike"]
            iv = contract["impliedVolatility"]
            stats = _historical_strike_stats(close_values, high_values, low_values, strike / spot, sessions, option_type)
            contract_greeks = _model_greeks(option_type, spot, strike, years, iv, rate_decimal, dividend_yield) if rate_decimal is not None and iv is not None else None
            implied_expected_move = iv * math.sqrt(days_to_expiration / 365) * 100 if iv is not None else None
            gap_pct = abs((strike / spot - 1) * 100)
            contract.update({
                "distancePct": (strike / spot - 1) * 100,
                "historicalExpectedMovePct": historical_expected_move,
                "impliedExpectedMovePct": implied_expected_move,
                "distanceInHistoricalMoves": gap_pct / historical_expected_move if historical_expected_move else None,
                "distanceInImpliedMoves": gap_pct / implied_expected_move if implied_expected_move else None,
                "breakEven": strike - contract["mark"] if option_type == "PUT" and contract["mark"] is not None else strike + contract["mark"] if option_type == "CALL" and contract["mark"] is not None else None,
                "greeks": contract_greeks,
                "historical": stats,
            })
            output.append(contract)
        stamp = history.index[-1]
        data_date = stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return {
            "symbol": symbol, "optionType": option_type, "expiration": expiration,
            "daysToExpiration": days_to_expiration, "underlyingPrice": spot,
            "historyDataDate": data_date, "retrievedAt": now, "lookback": lookback,
            "horizonSessions": sessions, "sampleWindows": windows,
            "historicalVolatility20dPct": hv20, "historicalVolatility60dPct": hv60,
            "historicalExpectedMovePct": historical_expected_move,
            "horizonReturns": {"averagePct": avg_return, "minimumPct": min_return, "maximumPct": max_return},
            "riskFreeRatePct": rate, "riskFreeRateDate": treasury["asOf"],
            "trailingDividendYieldPct": dividend_yield * 100,
            "greeksModel": "Black-Scholes European approximation; per share; IV from selected contract",
            "contracts": output, "source": "Yahoo Finance via yfinance",
        }

    try:
        return _cached(("option_research", symbol, expiration, option_type, lookback), 90, load)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Option strike research failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Option research data is temporarily unavailable.") from error


@app.get("/api/wheel")
def list_wheel_cycles() -> list[dict[str, Any]]:
    try:
        return wheel.list_cycles()
    except Exception as error:
        logger.exception("Wheel database could not be read")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


@app.get("/api/wheel/alerts")
def get_wheel_background_alerts() -> list[dict[str, Any]]:
    try:
        return market_radar.list_wheel_alerts()
    except Exception as error:
        logger.exception("Wheel alerts could not be read")
        raise HTTPException(status_code=503, detail="Wheel alert storage is unavailable.") from error


@app.post("/api/wheel/alerts/{alert_id}/dismiss")
def dismiss_wheel_background_alert(alert_id: int) -> dict[str, bool]:
    try:
        if not market_radar.dismiss_wheel_alert(alert_id):
            raise HTTPException(status_code=404, detail="Active alert not found.")
        return {"dismissed": True}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Wheel alert could not be dismissed")
        raise HTTPException(status_code=503, detail="Wheel alert storage is unavailable.") from error


@app.get("/api/market/radar")
def get_market_radar() -> dict[str, Any]:
    try:
        return market_radar.latest_radar()
    except Exception as error:
        logger.exception("Market radar could not be read")
        raise HTTPException(status_code=503, detail="Market radar storage is unavailable.") from error


@app.get("/api/market/radar/watchlist")
def get_market_radar_watchlist() -> list[dict[str, str]]:
    try:
        return market_radar.list_watchlist()
    except Exception as error:
        logger.exception("Radar watchlist could not be read")
        raise HTTPException(status_code=503, detail="Market watchlist is unavailable.") from error


@app.post("/api/market/radar/watchlist")
def add_market_radar_symbol(payload: dict[str, Any]) -> dict[str, str]:
    try:
        return market_radar.add_watch_symbol(str(payload.get("symbol", "")), str(payload.get("name") or ""))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Radar watchlist symbol could not be added")
        raise HTTPException(status_code=503, detail="Market watchlist is unavailable.") from error


@app.delete("/api/market/radar/watchlist/{symbol}")
def remove_market_radar_symbol(symbol: str) -> dict[str, bool]:
    try:
        if not market_radar.remove_watch_symbol(symbol):
            raise HTTPException(status_code=404, detail="Ticker is not in the custom watchlist.")
        return {"removed": True}
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Radar watchlist symbol could not be removed")
        raise HTTPException(status_code=503, detail="Market watchlist is unavailable.") from error


@app.post("/api/market/radar/scan")
def scan_market_radar() -> dict[str, Any]:
    try:
        universe = list(POPULAR_STOCKS) + [item for item in EARNINGS_WATCHLIST if item["symbol"] not in {s["symbol"] for s in POPULAR_STOCKS}]
        universe.append({"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"})
        universe.extend({"symbol": cycle["symbol"], "name": cycle["symbol"]} for cycle in wheel.list_cycles())
        universe.extend(market_radar.list_watchlist())
        return market_radar.run_radar(universe)
    except Exception as error:
        logger.exception("Market radar scan failed")
        raise HTTPException(status_code=502, detail="Market data scan failed. Try again later.") from error


@app.post("/api/wheel")
def create_wheel_cycle(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return wheel.create_cycle(payload, _symbol(str(payload.get("symbol", ""))))
    except wheel.WheelError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Wheel cycle could not be created")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


@app.get("/api/wheel/{cycle_id}")
def get_wheel_cycle(cycle_id: str) -> dict[str, Any]:
    try:
        return wheel.get_cycle(cycle_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Wheel cycle could not be read")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


@app.delete("/api/wheel/{cycle_id}", status_code=204)
def delete_wheel_cycle(cycle_id: str) -> None:
    try:
        wheel.delete_cycle(cycle_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        logger.exception("Wheel cycle could not be deleted")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


@app.post("/api/wheel/{cycle_id}/actions/{action}")
def update_wheel_cycle(cycle_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return wheel.transition(cycle_id, action, payload)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except wheel.WheelError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        logger.exception("Wheel cycle could not be updated")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


@app.get("/api/wheel/{cycle_id}/analysis")
def analyze_wheel_cycle(cycle_id: str) -> dict[str, Any]:
    try:
        cycle = wheel.get_cycle(cycle_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    leg = cycle["activeLeg"]
    if not leg:
        return {"cycleId": cycle_id, "state": cycle["state"], "alerts": [], "marketAvailable": False}
    try:
        ticker = yf.Ticker(cycle["symbol"])
        try:
            fast_info = dict(ticker.fast_info)
        except Exception:
            fast_info = {}
        underlying = _number(_safe_dict_get(fast_info, "last_price"))
        if underlying is None:
            history = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if history is not None and not history.empty:
                underlying = _number(history["Close"].dropna().iloc[-1])
        chain = ticker.option_chain(leg["expiration"])
        frame = chain.puts if leg["type"] == "PUT" else chain.calls
        matches = frame[frame["strike"].sub(leg["strike"]).abs() < 0.001] if frame is not None and not frame.empty else None
        quote: dict[str, Any] | None = None
        if matches is not None and not matches.empty:
            quote = _option_contracts(matches).pop(0)
        mark = quote.get("mark") if quote else None
        days = (date.fromisoformat(leg["expiration"]) - date.today()).days
        contracts = leg["contracts"]
        premium = leg["premium"]
        quantity = contracts * 100
        unrealized = (premium - mark) * quantity if mark is not None else None
        captured = ((premium - mark) / premium * 100) if mark is not None and premium > 0 else None
        alerts = []
        if underlying is not None:
            if leg["type"] == "PUT":
                if underlying < leg["strike"]:
                    alerts.append({"level": "watch", "code": "put_itm", "message": "Underlying is below the put strike; assignment is possible."})
                breakeven = leg["strike"] - premium
                if underlying <= breakeven:
                    alerts.append({"level": "risk", "code": "put_breakeven", "message": "Underlying is at or below the put break-even at expiration."})
            else:
                basis = cycle["shareCostBasis"]
                breakeven = (basis - premium) if basis is not None else None
                if underlying > leg["strike"]:
                    alerts.append({"level": "watch", "code": "call_itm", "message": "Underlying is above the call strike; covered shares may be called away."})
                if basis is not None and underlying < basis:
                    alerts.append({"level": "watch", "code": "below_cost_basis", "message": "Underlying is below the recorded share cost basis."})
        else:
            basis = cycle["shareCostBasis"]
            breakeven = leg["strike"] - premium if leg["type"] == "PUT" else ((basis - premium) if basis is not None else None)
        assignment_pnl = None
        if leg["type"] == "CALL" and cycle["shareCostBasis"] is not None:
            assignment_pnl = (leg["strike"] + premium - cycle["shareCostBasis"]) * quantity
        if cycle["takeProfitPercent"] is not None and captured is not None and captured >= cycle["takeProfitPercent"]:
            alerts.append({"level": "action", "code": "take_profit", "message": f"Configured premium-capture alert reached ({captured:.0f}% captured)."})
        if cycle["maxLossDollars"] is not None and unrealized is not None and unrealized <= -cycle["maxLossDollars"]:
            alerts.append({"level": "risk", "code": "max_loss", "message": "Configured loss threshold reached based on the current option mark."})
        if days <= cycle["expiryAlertDays"]:
            alerts.append({"level": "watch", "code": "expiration_soon", "message": f"{days} days remain to expiration; confirm the broker's expiration and assignment outcome."})
        if not quote:
            alerts.append({"level": "info", "code": "quote_unavailable", "message": "No matching option quote is available; automatic premium alerts are paused."})
        if not (underlying is not None and quote is not None):
            review_guidance = {"status": "Data incomplete", "message": "Wait for a current underlying price and matching option quote before using market-based checks. Confirm quotes at your broker."}
        elif days <= 0:
            review_guidance = {"status": "Confirm expiration outcome", "message": "The expiration date has arrived. Check your broker for assignment or expiration status, then record the confirmed transition."}
        elif cycle["takeProfitPercent"] is not None and captured is not None and captured >= cycle["takeProfitPercent"]:
            review_guidance = {"status": "Review configured profit threshold", "message": f"The position has captured about {captured:.0f}% of its opening credit. Compare the remaining credit with your saved rule and closing costs before deciding whether to close."}
        elif cycle["maxLossDollars"] is not None and unrealized is not None and unrealized <= -cycle["maxLossDollars"]:
            review_guidance = {"status": "Review configured loss threshold", "message": "The current option mark crosses your saved loss threshold. Check the live bid/ask and your planned risk response."}
        elif days <= cycle["expiryAlertDays"]:
            review_guidance = {"status": "Monitor near expiration", "message": "Expiration is within your alert window. Review the underlying versus strike, after-hours movement, and your broker's assignment process."}
        elif (leg["type"] == "PUT" and underlying < leg["strike"]) or (leg["type"] == "CALL" and underlying > leg["strike"]):
            review_guidance = {"status": "Monitor assignment exposure", "message": "The underlying is past the option strike. Assignment is possible; review the shares or cash exposure you would accept."}
        else:
            review_guidance = {"status": "Continue monitoring", "message": "No saved threshold is currently met. If the option expires OTM, confirm the result with your broker; if assigned, record shares and continue the wheel from that state."}
        next_states = ("PUT_CASH_READY after OTM expiry or closing; SHARES_HELD if assigned" if leg["type"] == "PUT"
                       else "SHARES_HELD after OTM expiry or closing; PUT_CASH_READY if all covered shares are assigned")
        return {"cycleId": cycle_id, "state": cycle["state"], "underlyingPrice": underlying,
                "optionMark": mark, "bid": quote.get("bid") if quote else None,
                "ask": quote.get("ask") if quote else None, "unrealizedPnl": unrealized,
                "premiumCapturedPercent": captured, "breakEvenAtExpiration": breakeven,
                "coveredCallAssignmentPnl": assignment_pnl,
                "daysToExpiration": days, "nextScenarios": next_states, "alerts": alerts,
                "reviewGuidance": review_guidance,
                "marketAvailable": underlying is not None and quote is not None,
                "dataSource": "Yahoo Finance via yfinance; quotes may be delayed or unavailable"}
    except Exception as error:
        logger.info("Wheel analysis unavailable for %s: %s", cycle["symbol"], error)
        return {"cycleId": cycle_id, "state": cycle["state"], "alerts": [
            {"level": "info", "code": "market_unavailable", "message": "Current option analysis is unavailable. Recorded trades remain safe in SQLite."}
        ], "marketAvailable": False}


@app.get("/api/market/{symbol}/overview")
def stock_overview(symbol: str) -> dict[str, Any]:
    symbol = _symbol(symbol)

    def load() -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        try:
            info = ticker.info or {}
        except Exception as error:
            logger.info("Quote details unavailable for %s: %s", symbol, error)
            info = {}
        try:
            fast_info = dict(ticker.fast_info)
        except Exception:
            fast_info = {}
        price = _number(info.get("regularMarketPrice")) or _number(info.get("currentPrice")) or _number(_safe_dict_get(fast_info, "last_price"))
        previous = _number(info.get("regularMarketPreviousClose")) or _number(info.get("previousClose")) or _number(_safe_dict_get(fast_info, "previous_close"))
        change = price - previous if price is not None and previous is not None else None
        change_percent = change / previous * 100 if change is not None and previous else None
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "exchange": info.get("fullExchangeName") or info.get("exchange") or _safe_dict_get(fast_info, "exchange"),
            "currency": info.get("currency") or _safe_dict_get(fast_info, "currency") or "USD",
            "price": price,
            "previousClose": previous,
            "change": change,
            "changePercent": change_percent,
            "marketCap": _number(info.get("marketCap")) or _number(_safe_dict_get(fast_info, "market_cap")),
            "trailingPE": _number(info.get("trailingPE")),
            "forwardPE": _number(info.get("forwardPE")),
            "eps": _number(info.get("trailingEps")),
            "dividendYield": _number(info.get("dividendYield")),
            "dividendRate": _number(info.get("dividendRate")),
            "yearLow": _number(info.get("fiftyTwoWeekLow")) or _number(_safe_dict_get(fast_info, "year_low")),
            "yearHigh": _number(info.get("fiftyTwoWeekHigh")) or _number(_safe_dict_get(fast_info, "year_high")),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "summary": info.get("longBusinessSummary"),
            "source": "Yahoo Finance via yfinance",
        }

    try:
        return _cached(("overview", symbol), 300, load)
    except Exception as error:
        logger.exception("Market overview request failed for %s", symbol)
        raise HTTPException(status_code=502, detail="The market data source could not load this ticker. Try again shortly.") from error


@app.get("/api/market/{symbol}/history")
def stock_history(symbol: str, lookback: str = "1D", interval: str = "5m") -> dict[str, Any]:
    symbol = _symbol(symbol)
    lookback = lookback.upper()
    if lookback not in LOOKBACKS:
        raise HTTPException(status_code=422, detail="Choose a supported chart lookback.")
    period, intervals = LOOKBACKS[lookback]
    if interval not in intervals:
        raise HTTPException(status_code=422, detail=f"Interval {interval} is not available for {lookback}.")

    def load() -> dict[str, Any]:
        history = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False, actions=False)
        if history is None or history.empty:
            raise HTTPException(status_code=404, detail="No historical prices were returned for this ticker and range.")
        bars = []
        for stamp, row in history.iterrows():
            try:
                epoch = int(stamp.timestamp() * 1000)
            except (AttributeError, OSError, ValueError):
                continue
            bar = {
                "time": epoch,
                "open": _number(row.get("Open")),
                "high": _number(row.get("High")),
                "low": _number(row.get("Low")),
                "close": _number(row.get("Close")),
                "volume": _number(row.get("Volume")) or 0,
            }
            if all(bar[key] is not None for key in ("open", "high", "low", "close")):
                bars.append(bar)
        return {"symbol": symbol, "lookback": lookback, "interval": interval, "bars": bars}

    try:
        return _cached(("history", symbol, lookback, interval), 90, load)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Price history request failed for %s", symbol)
        raise HTTPException(status_code=502, detail="The market data source could not load price history. Try again shortly.") from error


@app.get("/api/market/{symbol}/financials")
def stock_financials(symbol: str, statement: str = "income", frequency: str = "annual") -> dict[str, Any]:
    symbol = _symbol(symbol)
    if statement not in {"income", "balance", "cashflow"}:
        raise HTTPException(status_code=422, detail="Choose income, balance, or cashflow.")
    if frequency not in {"annual", "quarterly"}:
        raise HTTPException(status_code=422, detail="Choose annual or quarterly reports.")

    def load() -> dict[str, Any]:
        ticker = yf.Ticker(symbol)
        frame = _statement_frame(ticker, statement, frequency)
        return _statement_payload(frame)

    try:
        return _cached(("financials", symbol, statement, frequency), 3600, load)
    except Exception as error:
        logger.exception("Financial statement request failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Financial statement data is temporarily unavailable.") from error


@app.get("/api/market/{symbol}/dividends")
def stock_dividends(symbol: str) -> dict[str, Any]:
    symbol = _symbol(symbol)

    def load() -> dict[str, Any]:
        series = yf.Ticker(symbol).dividends
        if series is None or getattr(series, "empty", True):
            return {"symbol": symbol, "events": []}
        events = []
        for stamp, amount in series.tail(30).sort_index(ascending=False).items():
            value = _number(amount)
            if value is not None:
                events.append({"date": stamp.strftime("%Y-%m-%d"), "amount": value})
        return {"symbol": symbol, "events": events}

    try:
        return _cached(("dividends", symbol), 3600, load)
    except Exception as error:
        logger.exception("Dividend history request failed for %s", symbol)
        raise HTTPException(status_code=502, detail="Dividend history is temporarily unavailable.") from error


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/documents")
def list_documents() -> list[dict[str, str]]:
    return [
        {
            "path": path.relative_to(DOCS_ROOT).as_posix(),
            "title": _title_for(path),
        }
        for path in _document_files()
    ]


@app.get("/api/documents/{document_path:path}")
def get_document(document_path: str) -> dict[str, str]:
    requested = (DOCS_ROOT / document_path).resolve()
    if (
        not requested.is_relative_to(DOCS_ROOT)
        or requested.suffix.lower() != ".md"
        or not requested.is_file()
        or any(part.startswith(".") for part in requested.relative_to(DOCS_ROOT).parts)
    ):
        raise HTTPException(status_code=404, detail="Markdown document not found")
    return {
        "path": requested.relative_to(DOCS_ROOT).as_posix(),
        "title": _title_for(requested),
        "content": requested.read_text(encoding="utf-8", errors="replace"),
    }


if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{requested_path:path}", include_in_schema=False)
def frontend(requested_path: str) -> FileResponse:
    return _frontend_index()
