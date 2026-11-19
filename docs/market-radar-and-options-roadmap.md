# Market radar and options research roadmap

## What the first version does

The Market Radar scans the app's preset stock and earnings watchlists plus tickers in tracked wheel cycles. It saves daily adjusted-price snapshots in the same SQLite database as wheel cycles. Its “trend checks” count four observable conditions: price above the 20-day average, the 20-day average above the 50-day average, positive 20-day return, and outperformance versus SPY over 20 days. The score is a filter for further reading, not a forecast, probability, target price, or recommendation.

Top movers are ranked by the latest daily return in the saved scan. Daily snapshots are retained for the latest 120 scans. Quote/history errors are kept with the scan, and the page shows the data date to make stale results visible.

The scheduled market monitor runs every 15 minutes. During US weekday regular trading hours it rechecks the active option leg for alerts that match the thresholds recorded on that wheel cycle. Alerts are saved, deduplicated while the same condition remains active, and can be dismissed; a resolved condition that appears again creates a fresh review alert. After 4:20 p.m. New York time on weekdays, it creates one radar snapshot for that session date. The monitor is a systemd user timer installed by the SSD migration helper.

## Next useful improvements

1. Let the user select a research universe (watchlists, sectors, indexes, or manually entered symbols), and show the universe size and scan coverage explicitly.
2. Add context to each candidate: upcoming earnings, sector and benchmark comparison, valuation and financial trends, volatility, liquidity, and relevant filings. Keep the raw metric, source, and timestamp visible.
3. Add portfolio and wheel exposure views: cash collateral, share concentration, assignment outcomes, ex-dividend and earnings dates, and scenario tables for underlying price moves. Treat early assignment and gaps as real possibilities.
4. Allow named, versioned rule sets with user-chosen thresholds. Store every signal's input data and rule version so a later backtest can reproduce what the app knew at the time.
5. Build backtests on point-in-time data, include delisted companies and corporate actions, and model bid/ask spread, commissions, slippage, assignment, and cash usage. Split development and evaluation periods, reserve a final out-of-sample period, and compare against a simple benchmark. Avoid repeatedly tuning on the same history.
6. Run a paper-trading period with recorded decisions and fills before considering any live brokerage integration. Keep the user in control of each transition and make alerts explain what condition fired and what could invalidate it.

## Options-specific guardrails

The wheel is a workflow for selling puts and covered calls, not a guaranteed income strategy. A cash-secured put can lead to owning a falling stock; a covered call limits upside above its strike while the stock can still fall. Assignment, liquidity, volatility, and early exercise matter. Each position should show max cash/share exposure, break-even assumptions, current quote timestamp, and outcomes at several underlying prices and expirations.

Do not label a strategy “best” or “profitable” based on a historical fit. The Options Clearing Corporation's disclosure document describes standardized-options risks, including assignment and the payoff tradeoffs of covered calls. Hypothetical performance has material limits; the SEC warns that projections and performance claims can mislead. Backtest overfitting research shows that trying many configurations increases the chance of selecting a rule that only fits the sample.

Sources: [OCC Options Disclosure Document](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document), [SEC Investor.gov on performance claims](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-47), and [Bailey et al. on backtest overfitting](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2423465_code434076.pdf?abstractid=2308659&mirid=1).
