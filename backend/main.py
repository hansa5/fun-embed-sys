"""FastAPI endpoints and production static-file serving for the React UI."""
from __future__ import annotations

import logging
import math
from pathlib import Path
import re
import threading
import time
from datetime import date
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yfinance as yf
from backend import wheel

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


@app.get("/api/wheel")
def list_wheel_cycles() -> list[dict[str, Any]]:
    try:
        return wheel.list_cycles()
    except Exception as error:
        logger.exception("Wheel database could not be read")
        raise HTTPException(status_code=503, detail="Wheel tracking storage is unavailable.") from error


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
        next_states = ("PUT_CASH_READY after OTM expiry or closing; SHARES_HELD if assigned" if leg["type"] == "PUT"
                       else "SHARES_HELD after OTM expiry or closing; PUT_CASH_READY if all covered shares are assigned")
        return {"cycleId": cycle_id, "state": cycle["state"], "underlyingPrice": underlying,
                "optionMark": mark, "bid": quote.get("bid") if quote else None,
                "ask": quote.get("ask") if quote else None, "unrealizedPnl": unrealized,
                "premiumCapturedPercent": captured, "breakEvenAtExpiration": breakeven,
                "coveredCallAssignmentPnl": assignment_pnl,
                "daysToExpiration": days, "nextScenarios": next_states, "alerts": alerts,
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
