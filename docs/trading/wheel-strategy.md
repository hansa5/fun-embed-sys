# Wheel strategy tracker

The Wheel Strategy page records a manually managed options cycle. It does not
place orders, connect to a brokerage, or decide which contract is best. Option
quotes come from Yahoo Finance through `yfinance` and may be delayed, sparse,
or unavailable. Use your broker's fills and assignment notices as the source of
truth.

## State flow

```text
PUT_OPEN
  ├─ buy to close ───────────────> PUT_CASH_READY
  ├─ confirmed OTM expiration ───> PUT_CASH_READY
  └─ broker confirms assignment -> SHARES_HELD

PUT_CASH_READY
  ├─ sell another put ──────────> PUT_OPEN
  └─ close cycle ───────────────> CLOSED

SHARES_HELD
  ├─ sell covered call ─────────> CALL_OPEN
  └─ record share sale ─────────> SHARES_HELD or PUT_CASH_READY

CALL_OPEN
  ├─ buy to close ──────────────> SHARES_HELD
  ├─ confirmed OTM expiration ──> SHARES_HELD
  └─ broker confirms assignment -> SHARES_HELD or PUT_CASH_READY
```

The assignment action is an explicit manual record. An option being in the
money does not prove that the broker assigned it. A short call may cover only
some of the shares; the remaining shares stay in `SHARES_HELD`. A cycle can be
closed only when it has no open option and no recorded shares.

The page shows the current state in green in an interactive state diagram.
Choose a reachable state or a transition card to review the destination,
trade-specific estimates, and required inputs before recording the move. The
ticker selector includes the target list (including Amazon and Bank of
America); custom tickers can be added to that browser's local target list.
Cycles can be deleted from the list after a confirmation prompt. Deleting a
cycle permanently removes its option legs and event history from SQLite.

## Record a cycle

Start with a cash-secured put by choosing the symbol, expiration, strike,
contract count, and the actual credit received per share. The app shows
indicative bid/ask data beside the contract selector. Enter your fill, since
the displayed quote may differ from the trade. The displayed put collateral
is strike × 100 × contracts; verify that amount against your own account.

You can also start from shares already owned by entering the number of shares
and your average economic cost per share. The app will only allow covered calls
for the number of full 100-share lots recorded.

Each close, expiration, assignment, sale, and new option sale is written to an
append-only event history for that cycle. The database stores option details,
state changes, user-set alert thresholds, and notes. It does not store account
credentials or broker data.

## Analysis and alerts

For an open option, the page checks the underlying price, a matching option
mark when available, estimated open P&L, premium captured, expiration days,
and break-even at expiration. It flags the option being in the money, the
underlying crossing break-even, an optional profit-capture threshold, an
optional dollar loss threshold, and the configured expiration window.

Profit alerts are based on `(opening credit − current option mark) ÷ opening
credit`. The initial expiry alert is seven days and can be changed on each new
cycle. Blank profit and loss thresholds remain disabled. Alerts are visible
inside this page while it refreshes; this version does not send push, email,
or background notifications while the app is closed.

These alerts describe recorded conditions, not a best action or a prediction
of assignment. Intrinsic value, option marks, cost basis, and realized P&L are
simplified estimates. Values exclude commissions, taxes, interest, dividends,
corporate actions, and broker-specific assignment handling. Put assignment
records an economic share basis of strike less the put credit; this is not tax
basis guidance. A covered-call assignment records share P&L using the recorded
share basis and call credit.

## Data and access limits

Option chains and underlying prices are fetched from Yahoo Finance through
`yfinance`. The app does not provide an execution-quality quote or guarantee
that a listed contract has a usable bid, ask, or open-interest figure. If a
matching quote is missing, automatic premium alerts pause while the manually
recorded position remains available.

Wheel records are private to this app instance but the existing app does not
have user login. Keep it on trusted local or Tailscale access; do not expose it
through Tailscale Funnel or another public endpoint until app authentication
and authorization are implemented.

## SQLite location

The database defaults to `data/wheel.sqlite3` under the repository root. On
the Raspberry Pi, that is `/mnt/saman-ssd/git_repo/fun-embed-sys/data/wheel.sqlite3`.
Set `FUN_EMBED_DB_PATH` to an absolute path to place it elsewhere. Raspberry
Pi SSD and mount details are documented in [Pi storage](../rpi/storage.md).
