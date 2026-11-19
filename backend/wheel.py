"""SQLite persistence and explicit state transitions for wheel cycles."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import uuid
from contextlib import contextmanager
from typing import Any, Iterator


class WheelError(ValueError):
    """Invalid wheel-cycle input or transition."""


def database_path() -> Path:
    configured = os.environ.get("FUN_EMBED_DB_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "data" / "wheel.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        connection.executescript(
            """
        CREATE TABLE IF NOT EXISTS wheel_cycles (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            state TEXT NOT NULL,
            shares INTEGER NOT NULL DEFAULT 0,
            share_cost_basis REAL,
            realized_pnl REAL NOT NULL DEFAULT 0,
            take_profit_percent REAL,
            max_loss_dollars REAL,
            expiry_alert_days INTEGER NOT NULL DEFAULT 7,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS wheel_legs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL REFERENCES wheel_cycles(id) ON DELETE CASCADE,
            sequence INTEGER NOT NULL,
            option_type TEXT NOT NULL CHECK(option_type IN ('PUT', 'CALL')),
            strike REAL NOT NULL,
            expiration TEXT NOT NULL,
            contracts INTEGER NOT NULL CHECK(contracts > 0),
            premium REAL NOT NULL CHECK(premium >= 0),
            status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED', 'EXPIRED', 'ASSIGNED')),
            close_price REAL,
            opened_at TEXT NOT NULL,
            closed_at TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_leg_per_cycle
            ON wheel_legs(cycle_id) WHERE status = 'OPEN';
        CREATE TABLE IF NOT EXISTS wheel_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT NOT NULL REFERENCES wheel_cycles(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            from_state TEXT,
            to_state TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _number(value: Any, label: str, *, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise WheelError(f"{label} must be a number.") from None
    if result != result or result in (float("inf"), float("-inf")):
        raise WheelError(f"{label} must be finite.")
    if minimum is not None and result < minimum:
        raise WheelError(f"{label} must be at least {minimum}.")
    return result


def _integer(value: Any, label: str, *, minimum: int = 1) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise WheelError(f"{label} must be a whole number.") from None
    if isinstance(value, float) and not value.is_integer():
        raise WheelError(f"{label} must be a whole number.")
    if isinstance(value, str) and value.strip() != str(result):
        raise WheelError(f"{label} must be a whole number.")
    if result < minimum:
        raise WheelError(f"{label} must be at least {minimum}.")
    return result


def _expiration(value: Any) -> str:
    try:
        result = date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise WheelError("Expiration must be a valid YYYY-MM-DD date.") from None
    if result < date.today():
        raise WheelError("Expiration must not be in the past.")
    return result.isoformat()


def _cycle_row(connection: sqlite3.Connection, cycle_id: str) -> sqlite3.Row:
    cycle = connection.execute("SELECT * FROM wheel_cycles WHERE id = ?", (cycle_id,)).fetchone()
    if cycle is None:
        raise LookupError("Wheel cycle not found.")
    return cycle


def _open_leg(connection: sqlite3.Connection, cycle_id: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM wheel_legs WHERE cycle_id = ? AND status = 'OPEN'", (cycle_id,)
    ).fetchone()


def _leg_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"], "type": row["option_type"], "strike": row["strike"],
        "expiration": row["expiration"], "contracts": row["contracts"],
        "premium": row["premium"], "status": row["status"],
        "openedAt": row["opened_at"], "closePrice": row["close_price"],
    }


def _cycle_dict(connection: sqlite3.Connection, row: sqlite3.Row, *, with_events: bool = False) -> dict[str, Any]:
    result = {
        "id": row["id"], "symbol": row["symbol"], "state": row["state"],
        "shares": row["shares"], "shareCostBasis": row["share_cost_basis"],
        "realizedPnl": row["realized_pnl"], "takeProfitPercent": row["take_profit_percent"],
        "maxLossDollars": row["max_loss_dollars"], "expiryAlertDays": row["expiry_alert_days"],
        "notes": row["notes"], "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        "activeLeg": _leg_dict(_open_leg(connection, row["id"])),
    }
    if with_events:
        events = connection.execute(
            "SELECT * FROM wheel_events WHERE cycle_id = ? ORDER BY id DESC", (row["id"],)
        ).fetchall()
        result["events"] = [{
            "id": item["id"], "type": item["event_type"], "fromState": item["from_state"],
            "toState": item["to_state"], "details": json.loads(item["details_json"]),
            "createdAt": item["created_at"],
        } for item in events]
    return result


def _event(connection: sqlite3.Connection, cycle_id: str, event_type: str, from_state: str,
           to_state: str, details: dict[str, Any]) -> None:
    connection.execute(
        "INSERT INTO wheel_events(cycle_id, event_type, from_state, to_state, details_json, created_at) VALUES(?, ?, ?, ?, ?, ?)",
        (cycle_id, event_type, from_state, to_state, json.dumps(details, allow_nan=False), _now()),
    )


def _insert_leg(connection: sqlite3.Connection, cycle_id: str, option_type: str, data: dict[str, Any]) -> int:
    contracts = _integer(data.get("contracts"), "Contracts")
    strike = _number(data.get("strike"), "Strike", minimum=0.01)
    premium = _number(data.get("premium"), "Premium", minimum=0)
    expiration = _expiration(data.get("expiration"))
    sequence = connection.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM wheel_legs WHERE cycle_id = ?", (cycle_id,)
    ).fetchone()[0]
    cursor = connection.execute(
        "INSERT INTO wheel_legs(cycle_id, sequence, option_type, strike, expiration, contracts, premium, status, opened_at) VALUES(?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)",
        (cycle_id, sequence, option_type, strike, expiration, contracts, premium, _now()),
    )
    return int(cursor.lastrowid)


def create_cycle(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    mode = payload.get("startMode", "put")
    if mode not in {"put", "shares"}:
        raise WheelError("Choose a starting mode of put or shares.")
    cycle_id = str(uuid.uuid4())
    now = _now()
    take_profit = payload.get("takeProfitPercent")
    max_loss = payload.get("maxLossDollars")
    take_profit = None if take_profit in (None, "") else _number(take_profit, "Take-profit alert", minimum=1)
    if take_profit is not None and take_profit > 99.9:
        raise WheelError("Take-profit alert must be below 100%.")
    max_loss = None if max_loss in (None, "") else _number(max_loss, "Loss alert", minimum=0.01)
    expiry_days = _integer(payload.get("expiryAlertDays", 7), "Expiry alert days", minimum=0)
    notes = str(payload.get("notes", "")).strip()[:2000]

    with _connect() as connection:
        if mode == "put":
            connection.execute(
                "INSERT INTO wheel_cycles(id, symbol, state, take_profit_percent, max_loss_dollars, expiry_alert_days, notes, created_at, updated_at) VALUES(?, ?, 'PUT_OPEN', ?, ?, ?, ?, ?, ?)",
                (cycle_id, symbol, take_profit, max_loss, expiry_days, notes, now, now),
            )
            _insert_leg(connection, cycle_id, "PUT", payload)
            _event(connection, cycle_id, "put_sold", "CASH_START", "PUT_OPEN", {"symbol": symbol})
        else:
            shares = _integer(payload.get("shares"), "Shares")
            basis = _number(payload.get("shareCostBasis"), "Average share cost", minimum=0.01)
            connection.execute(
                "INSERT INTO wheel_cycles(id, symbol, state, shares, share_cost_basis, take_profit_percent, max_loss_dollars, expiry_alert_days, notes, created_at, updated_at) VALUES(?, ?, 'SHARES_HELD', ?, ?, ?, ?, ?, ?, ?, ?)",
                (cycle_id, symbol, shares, basis, take_profit, max_loss, expiry_days, notes, now, now),
            )
            _event(connection, cycle_id, "shares_recorded", "CASH_START", "SHARES_HELD", {"shares": shares, "averageCost": basis})
        return _cycle_dict(connection, _cycle_row(connection, cycle_id))


def list_cycles() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute("SELECT * FROM wheel_cycles ORDER BY updated_at DESC").fetchall()
        return [_cycle_dict(connection, row) for row in rows]


def get_cycle(cycle_id: str) -> dict[str, Any]:
    with _connect() as connection:
        row = _cycle_row(connection, cycle_id)
        return _cycle_dict(connection, row, with_events=True)


def delete_cycle(cycle_id: str) -> None:
    """Remove one cycle and its event/leg history when the user deletes it."""
    with _connect() as connection:
        _cycle_row(connection, cycle_id)
        connection.execute("DELETE FROM wheel_cycles WHERE id = ?", (cycle_id,))


def transition(cycle_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    with _connect() as connection:
        cycle = _cycle_row(connection, cycle_id)
        state = cycle["state"]
        shares = cycle["shares"]
        basis = cycle["share_cost_basis"]
        pnl = cycle["realized_pnl"]
        leg = _open_leg(connection, cycle_id)
        details: dict[str, Any] = {}

        if action in {"sell_put", "sell_call"}:
            expected = "PUT_CASH_READY" if action == "sell_put" else "SHARES_HELD"
            if state != expected or leg is not None:
                raise WheelError(f"{action.replace('_', ' ').title()} is not valid from {state}.")
            option_type = "PUT" if action == "sell_put" else "CALL"
            contracts = _integer(payload.get("contracts"), "Contracts")
            if option_type == "CALL" and contracts * 100 > shares:
                raise WheelError("Covered-call contracts cannot cover more than the shares owned.")
            _insert_leg(connection, cycle_id, option_type, payload)
            new_state = "PUT_OPEN" if option_type == "PUT" else "CALL_OPEN"
            details = {"type": option_type, "strike": float(payload["strike"]), "expiration": _expiration(payload["expiration"]), "contracts": contracts, "premium": float(payload["premium"])}
        elif action in {"close_option", "expire_otm", "assigned"}:
            if leg is None or state not in {"PUT_OPEN", "CALL_OPEN"}:
                raise WheelError("There is no open option to resolve.")
            option_type = leg["option_type"]
            quantity = leg["contracts"] * 100
            credit = leg["premium"]
            strike = leg["strike"]
            if action == "close_option":
                close_price = _number(payload.get("closePrice"), "Buy-to-close price", minimum=0)
                leg_pnl = (credit - close_price) * quantity
                new_state = "PUT_CASH_READY" if option_type == "PUT" else "SHARES_HELD"
                connection.execute("UPDATE wheel_legs SET status = 'CLOSED', close_price = ?, closed_at = ? WHERE id = ?", (close_price, now, leg["id"]))
                connection.execute("UPDATE wheel_cycles SET realized_pnl = realized_pnl + ? WHERE id = ?", (leg_pnl, cycle_id))
                details = {"closePrice": close_price, "realizedOptionPnl": leg_pnl}
            elif action == "expire_otm":
                if date.fromisoformat(leg["expiration"]) > date.today():
                    raise WheelError("Record an OTM expiration only after the contract's expiration date.")
                leg_pnl = credit * quantity
                new_state = "PUT_CASH_READY" if option_type == "PUT" else "SHARES_HELD"
                connection.execute("UPDATE wheel_legs SET status = 'EXPIRED', close_price = 0, closed_at = ? WHERE id = ?", (now, leg["id"]))
                connection.execute("UPDATE wheel_cycles SET realized_pnl = realized_pnl + ? WHERE id = ?", (leg_pnl, cycle_id))
                details = {"result": "expired_out_of_money", "realizedOptionPnl": leg_pnl}
            else:
                connection.execute("UPDATE wheel_legs SET status = 'ASSIGNED', closed_at = ? WHERE id = ?", (now, leg["id"]))
                if option_type == "PUT":
                    new_shares = quantity
                    acquired_basis = strike - credit
                    old_value = (basis or 0) * shares
                    new_basis = (old_value + acquired_basis * new_shares) / (shares + new_shares)
                    connection.execute("UPDATE wheel_cycles SET shares = shares + ?, share_cost_basis = ? WHERE id = ?", (new_shares, new_basis, cycle_id))
                    new_state = "SHARES_HELD"
                    details = {"assignedShares": new_shares, "strike": strike, "economicCostBasisPerShare": acquired_basis}
                else:
                    if quantity > shares:
                        raise WheelError("Assignment quantity exceeds recorded shares.")
                    realized = (strike + credit - (basis or 0)) * quantity
                    remaining = shares - quantity
                    connection.execute("UPDATE wheel_cycles SET shares = ?, share_cost_basis = ?, realized_pnl = realized_pnl + ? WHERE id = ?", (remaining, basis if remaining else None, realized, cycle_id))
                    new_state = "PUT_CASH_READY" if remaining == 0 else "SHARES_HELD"
                    details = {"assignedSharesSold": quantity, "realizedWheelPnl": realized, "remainingShares": remaining}
        elif action == "sell_shares":
            if state != "SHARES_HELD" or leg is not None:
                raise WheelError("Shares can be sold after any open covered call is resolved.")
            quantity = _integer(payload.get("shares"), "Shares to sell")
            if quantity > shares:
                raise WheelError("Cannot sell more shares than the recorded holding.")
            price = _number(payload.get("price"), "Share sale price", minimum=0)
            realized = (price - (basis or 0)) * quantity
            remaining = shares - quantity
            connection.execute("UPDATE wheel_cycles SET shares = ?, share_cost_basis = ?, realized_pnl = realized_pnl + ? WHERE id = ?", (remaining, basis if remaining else None, realized, cycle_id))
            new_state = "PUT_CASH_READY" if remaining == 0 else "SHARES_HELD"
            details = {"sharesSold": quantity, "price": price, "realizedSharePnl": realized, "remainingShares": remaining}
        elif action == "close_cycle":
            if state != "PUT_CASH_READY" or shares != 0 or leg is not None:
                raise WheelError("Resolve open options and sell recorded shares before closing this cycle.")
            new_state = "CLOSED"
            details = {"result": "cycle_closed"}
        else:
            raise WheelError("Choose a supported wheel action.")

        connection.execute("UPDATE wheel_cycles SET state = ?, updated_at = ? WHERE id = ?", (new_state, now, cycle_id))
        _event(connection, cycle_id, action, state, new_state, details)
        return _cycle_dict(connection, _cycle_row(connection, cycle_id), with_events=True)
