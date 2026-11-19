"""Persistent, explainable daily market snapshots and wheel monitoring alerts."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Iterator

import yfinance as yf

from backend import wheel

logger = logging.getLogger(__name__)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    # This also initializes wheel_cycles before declaring its foreign key.
    wheel.list_cycles()
    connection = sqlite3.connect(wheel.database_path(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS radar_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            market_date TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            universe_count INTEGER NOT NULL,
            success_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            errors_json TEXT NOT NULL DEFAULT '[]'
        );
        CREATE INDEX IF NOT EXISTS radar_runs_latest ON radar_runs(id DESC);
        CREATE TABLE IF NOT EXISTS radar_watchlist (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS radar_items (
            run_id INTEGER NOT NULL REFERENCES radar_runs(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            data_date TEXT NOT NULL,
            close REAL NOT NULL,
            return_1d REAL,
            return_5d REAL,
            return_20d REAL,
            relative_strength_20d REAL,
            sma20 REAL,
            sma50 REAL,
            volume_ratio REAL,
            rsi14 REAL,
            trend_score INTEGER NOT NULL,
            setup TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            PRIMARY KEY (run_id, symbol)
        );
        CREATE TABLE IF NOT EXISTS wheel_background_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL REFERENCES wheel_cycles(id) ON DELETE CASCADE,
            alert_key TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            dismissed_at TEXT,
            UNIQUE (cycle_id, alert_key)
        );
        CREATE INDEX IF NOT EXISTS wheel_background_active
            ON wheel_background_alerts(is_active, dismissed_at, last_seen DESC);
        """
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _percent_change(new: float, old: float | None) -> float | None:
    if old is None or old == 0:
        return None
    return (new / old - 1) * 100


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    changes = [closes[index] - closes[index - 1] for index in range(len(closes) - period, len(closes))]
    gains = sum(max(change, 0) for change in changes) / period
    losses = sum(max(-change, 0) for change in changes) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100 - 100 / (1 + gains / losses)


def _fetch_one(stock: dict[str, str]) -> tuple[dict[str, Any] | None, str | None]:
    symbol = stock["symbol"]
    try:
        frame = yf.Ticker(symbol).history(period="6mo", interval="1d", auto_adjust=True, actions=False)
        if frame is None or frame.empty:
            return None, f"{symbol}: no daily price history returned"
        close_values = [float(value) for value in frame["Close"].dropna().tolist()]
        if len(close_values) < 21:
            return None, f"{symbol}: fewer than 21 daily closes"
        volume_values = [float(value) for value in frame["Volume"].fillna(0).tolist()]
        latest = close_values[-1]
        mean20 = sum(close_values[-20:]) / 20
        mean50 = sum(close_values[-50:]) / 50 if len(close_values) >= 50 else None
        average_prior_volume = sum(volume_values[-21:-1]) / 20 if len(volume_values) >= 21 else 0
        volume_ratio = volume_values[-1] / average_prior_volume if average_prior_volume > 0 else None
        stamp = frame.index[-1]
        data_date = stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10]
        return {
            "symbol": symbol, "name": stock.get("name", symbol), "dataDate": data_date,
            "close": latest, "return1d": _percent_change(latest, close_values[-2] if len(close_values) >= 2 else None),
            "return5d": _percent_change(latest, close_values[-6] if len(close_values) >= 6 else None),
            "return20d": _percent_change(latest, close_values[-21]),
            "sma20": mean20, "sma50": mean50, "volumeRatio": volume_ratio,
            "rsi14": _rsi(close_values),
        }, None
    except Exception as error:
        logger.info("Radar price history unavailable for %s: %s", symbol, error)
        return None, f"{symbol}: market data unavailable"


def _classify(row: dict[str, Any], benchmark_return: float | None) -> dict[str, Any]:
    close = row["close"]
    sma20 = row["sma20"]
    sma50 = row["sma50"]
    relative = row["return20d"] - benchmark_return if benchmark_return is not None else None
    checks = [
        {"label": "Price above 20-day average", "passed": close > sma20},
        {"label": "20-day average above 50-day average", "passed": sma50 is not None and sma20 > sma50},
        {"label": "Positive 20-day return", "passed": row["return20d"] > 0},
        {"label": "Outperformed SPY over 20 days", "passed": relative is not None and relative > 0},
    ]
    score = sum(bool(check["passed"]) for check in checks)
    if score >= 3:
        setup = "Trend alignment"
    elif close > (sma50 or 0) and close < sma20 and row["return20d"] > 0:
        setup = "Pullback in longer trend"
    elif close < sma20 and sma50 is not None and close < sma50:
        setup = "Weak trend context"
    else:
        setup = "Mixed signals"
    row.update({"relativeStrength20d": relative, "trendScore": score, "setup": setup, "evidence": checks})
    return row


def run_radar(universe: list[dict[str, str]]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    today_ny = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    unique: dict[str, dict[str, str]] = {}
    for stock in universe:
        symbol = str(stock.get("symbol", "")).strip().upper()
        if symbol and symbol not in unique:
            unique[symbol] = {"symbol": symbol, "name": str(stock.get("name") or symbol)}
    with ThreadPoolExecutor(max_workers=4) as executor:
        fetched = list(executor.map(_fetch_one, unique.values()))
    raw_rows = [row for row, error in fetched if row]
    errors = [error for _, error in fetched if error]
    spy = next((row for row in raw_rows if row["symbol"] == "SPY"), None)
    benchmark_return = spy["return20d"] if spy else None
    rows = [_classify(row, benchmark_return) for row in raw_rows]
    market_date = max((row["dataDate"] for row in rows), default=None)
    completed = datetime.now(timezone.utc)
    status = "complete" if rows else "unavailable"
    with _connect() as connection:
        cursor = connection.execute(
            "INSERT INTO radar_runs(session_date, market_date, status, started_at, completed_at, universe_count, success_count, error_count, errors_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (today_ny, market_date, status, started.isoformat(timespec="seconds"), completed.isoformat(timespec="seconds"), len(unique), len(rows), len(errors), json.dumps(errors[:100])),
        )
        run_id = int(cursor.lastrowid)
        for row in rows:
            connection.execute(
                "INSERT INTO radar_items(run_id,symbol,name,data_date,close,return_1d,return_5d,return_20d,relative_strength_20d,sma20,sma50,volume_ratio,rsi14,trend_score,setup,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, row["symbol"], row["name"], row["dataDate"], row["close"], row["return1d"], row["return5d"], row["return20d"], row["relativeStrength20d"], row["sma20"], row["sma50"], row["volumeRatio"], row["rsi14"], row["trendScore"], row["setup"], json.dumps(row["evidence"], allow_nan=False)),
            )
        connection.execute("DELETE FROM radar_runs WHERE id NOT IN (SELECT id FROM radar_runs ORDER BY id DESC LIMIT 120)")
    return {"runId": run_id, "sessionDate": today_ny, "marketDate": market_date, "status": status,
            "universeCount": len(unique), "successCount": len(rows), "errorCount": len(errors)}


def _item_payload(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "symbol": row["symbol"], "name": row["name"], "dataDate": row["data_date"],
        "close": row["close"], "return1d": row["return_1d"], "return5d": row["return_5d"],
        "return20d": row["return_20d"], "relativeStrength20d": row["relative_strength_20d"],
        "sma20": row["sma20"], "sma50": row["sma50"], "volumeRatio": row["volume_ratio"],
        "rsi14": row["rsi14"], "trendScore": row["trend_score"], "setup": row["setup"],
        "evidence": json.loads(row["evidence_json"]),
    }


def latest_radar() -> dict[str, Any]:
    with _connect() as connection:
        run = connection.execute("SELECT * FROM radar_runs ORDER BY id DESC LIMIT 1").fetchone()
        if run is None:
            return {"run": None, "items": [], "source": "Yahoo Finance via yfinance"}
        rows = connection.execute("SELECT * FROM radar_items WHERE run_id = ? ORDER BY trend_score DESC, return_1d DESC", (run["id"],)).fetchall()
        run_payload = {"id": run["id"], "sessionDate": run["session_date"], "marketDate": run["market_date"],
                       "status": run["status"], "scannedAt": run["completed_at"], "universeCount": run["universe_count"],
                       "successCount": run["success_count"], "errorCount": run["error_count"], "errors": json.loads(run["errors_json"])}
        return {"run": run_payload, "items": [_item_payload(row) for row in rows], "source": "Yahoo Finance via yfinance"}


def list_watchlist() -> list[dict[str, str]]:
    with _connect() as connection:
        return [{"symbol": row["symbol"], "name": row["name"]} for row in connection.execute("SELECT symbol,name FROM radar_watchlist ORDER BY symbol")]


def add_watch_symbol(symbol: str, name: str | None = None) -> dict[str, str]:
    symbol = symbol.strip().upper()
    if not symbol or len(symbol) > 15 or any(not (character.isalnum() or character in ".-") for character in symbol):
        raise ValueError("Ticker must contain 1–15 letters, numbers, dots, or hyphens.")
    payload = {"symbol": symbol, "name": (name or symbol).strip()[:100] or symbol}
    with _connect() as connection:
        connection.execute("INSERT INTO radar_watchlist(symbol,name,created_at) VALUES(?,?,?) ON CONFLICT(symbol) DO UPDATE SET name=excluded.name", (payload["symbol"], payload["name"], datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return payload


def remove_watch_symbol(symbol: str) -> bool:
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM radar_watchlist WHERE symbol=?", (symbol.strip().upper(),))
        return cursor.rowcount > 0


def persist_wheel_alerts(cycle: dict[str, Any], analysis: dict[str, Any]) -> None:
    leg = cycle.get("activeLeg")
    if not leg:
        active_codes: set[str] = set()
        reliable = True
    elif not analysis.get("marketAvailable"):
        # A failed or incomplete quote must not resolve an alert that was already seen.
        return
    else:
        reliable = True
        active_codes = {
            f"leg-{leg['id']}:{alert['code']}": alert
            for alert in analysis.get("alerts", [])
            if alert.get("level") in {"risk", "watch", "action"} and alert.get("code")
        }
    if not reliable:
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        for key, alert in active_codes.items():
            connection.execute(
                """INSERT INTO wheel_background_alerts(cycle_id,alert_key,level,message,evidence_json,first_seen,last_seen,is_active)
                   VALUES(?,?,?,?,?,?,?,1)
                   ON CONFLICT(cycle_id,alert_key) DO UPDATE SET
                     level=excluded.level, message=excluded.message, evidence_json=excluded.evidence_json,
                     last_seen=excluded.last_seen,
                     dismissed_at=CASE WHEN wheel_background_alerts.is_active=0 THEN NULL ELSE wheel_background_alerts.dismissed_at END,
                     is_active=1""",
                (cycle["id"], key, alert["level"], alert["message"], json.dumps({"underlyingPrice": analysis.get("underlyingPrice"),
                 "optionMark": analysis.get("optionMark"), "premiumCapturedPercent": analysis.get("premiumCapturedPercent"),
                 "daysToExpiration": analysis.get("daysToExpiration")}, allow_nan=False), now, now),
            )
        if active_codes:
            placeholders = ",".join("?" for _ in active_codes)
            connection.execute(f"UPDATE wheel_background_alerts SET is_active=0,dismissed_at=NULL WHERE cycle_id=? AND is_active=1 AND alert_key NOT IN ({placeholders})", (cycle["id"], *active_codes.keys()))
        else:
            connection.execute("UPDATE wheel_background_alerts SET is_active=0,dismissed_at=NULL WHERE cycle_id=? AND is_active=1", (cycle["id"],))


def run_wheel_monitor() -> dict[str, int]:
    # Import here to keep the market-data module independent of FastAPI at import time.
    from backend.main import analyze_wheel_cycle

    monitored = 0
    failed = 0
    for cycle in wheel.list_cycles():
        if not cycle.get("activeLeg"):
            persist_wheel_alerts(cycle, {})
            continue
        analysis = analyze_wheel_cycle(cycle["id"])
        if not analysis.get("marketAvailable"):
            failed += 1
            continue
        persist_wheel_alerts(cycle, analysis)
        monitored += 1
    return {"monitored": monitored, "failed": failed}


def list_wheel_alerts() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """SELECT a.*, c.symbol FROM wheel_background_alerts a
               JOIN wheel_cycles c ON c.id=a.cycle_id
               WHERE a.is_active=1 AND a.dismissed_at IS NULL
               ORDER BY CASE a.level WHEN 'risk' THEN 0 WHEN 'action' THEN 1 ELSE 2 END, a.last_seen DESC"""
        ).fetchall()
        return [{"id": row["id"], "cycleId": row["cycle_id"], "symbol": row["symbol"], "code": row["alert_key"],
                 "level": row["level"], "message": row["message"], "evidence": json.loads(row["evidence_json"]),
                 "firstSeen": row["first_seen"], "lastSeen": row["last_seen"]} for row in rows]


def dismiss_wheel_alert(alert_id: int) -> bool:
    with _connect() as connection:
        cursor = connection.execute("UPDATE wheel_background_alerts SET dismissed_at=? WHERE id=? AND is_active=1", (datetime.now(timezone.utc).isoformat(timespec="seconds"), alert_id))
        return cursor.rowcount > 0


def should_scan_after_close(now: datetime, latest: dict[str, Any]) -> bool:
    """Run the daily snapshot once after the regular US session on weekdays."""
    now = now.astimezone(ZoneInfo("America/New_York"))
    if now.weekday() >= 5 or now.hour < 16 or (now.hour == 16 and now.minute < 20):
        return False
    run = latest.get("run")
    if not run or run.get("sessionDate") != now.date().isoformat() or run.get("status") != "complete":
        return True
    try:
        scanned_at = datetime.fromisoformat(run["scannedAt"]).astimezone(ZoneInfo("America/New_York"))
    except (KeyError, TypeError, ValueError):
        return True
    # A manual scan before the close must not suppress the scheduled end-of-day snapshot.
    return scanned_at.date() != now.date() or (scanned_at.hour, scanned_at.minute) < (16, 20)
