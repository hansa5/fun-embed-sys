# Stock analysis workspace guide

This page explains the charts and company figures in the Stock Analysis view.
It is a learning aid for reading public company data, not a recommendation to
buy or sell a security.

## Find a company

Use the ticker search field to choose a popular symbol or enter another ticker
to look it up. The suggestions include common U.S. stocks and index funds.
Some listings use a market-specific suffix; if a symbol does not resolve, try
the symbol used by Yahoo Finance for that listing.

## Price chart

Choose a lookback range and bar size. Each candlestick represents one bar:

- **Open**: first reported price in the bar.
- **High**: highest reported price in the bar.
- **Low**: lowest reported price in the bar.
- **Close**: last reported price in the bar.
- **Volume**: number of shares traded during that bar.

For a candle, the body spans the open and close. The thin wick extends to the
high and low. The color indicates whether the close was above or below the
open. Hover over a candle with a mouse, or tap it on a phone, for the values
and a short explanation. Pan the chart horizontally to inspect neighboring
bars.

Bar sizes start at **one minute**. Yahoo Finance data accessed through
`yfinance` does not provide second-by-second quotes here. Intraday history is
limited by the source and the selected interval; the app offers coarser bars
for longer lookbacks so the displayed range matches the requested period.
The feed may be delayed or incomplete and is not suitable for execution.

Prices are shown in the listing currency and are not auto-adjusted in this
view. Splits and dividends can therefore create visible historical price
changes. Review corporate actions when comparing distant dates.

## Company metrics

- **Market price** is the latest quote returned by the provider. It may not be
  the current executable price.
- **Day change** compares the returned price with the previous close. Positive
  or negative color indicates direction, not whether the move is good or bad.
- **Market capitalization** estimates market value by multiplying share price
  by shares outstanding. It is not the price of one share or the company's
  cash balance.
- **Trailing P/E** divides price by earnings per share over the trailing year.
  It is difficult to interpret when earnings are negative or unusually high
  or low. Compare similar companies and read the statements.
- **Dividend yield** estimates annual dividends divided by the current share
  price. A changing price changes the yield; a company can reduce or stop its
  dividend.
- **52-week range** gives the reported high and low in the past year. It is
  historical context, not a forecast or a fair-value range.

No single metric gives a complete picture. Industry, accounting policies,
growth, debt, cash generation, and market conditions all affect how figures
should be read. A value that looks high or low needs context.

## Financial reports

The report panel shows annual or quarterly income statements, balance sheets,
and cash-flow statements when the source provides them. Dates label the
reporting periods. Hover over a row name for a plain-language description.
Values and available line items vary by company and filing period; this view
does not replace reading the company's official filings.

- **Income statement** reports revenue, expenses, and profit over a period.
- **Balance sheet** reports assets, liabilities, and equity at a point in
  time.
- **Cash-flow statement** reports cash movements from operations, investing,
  and financing over a period.

Accounting profit and cash generated are different measures. For example,
revenue does not mean the company has received that amount in cash, and net
income is not the same as operating cash flow.

## Dividends

Dividend events show the historical per-share amounts reported by the data
source. Past payments do not guarantee future payments. Dividend yield is a
ratio based on a recent price and the source's indicated annual amount; it can
change without any new dividend being declared.

## Data source and limits

The app uses the community `yfinance` package to read Yahoo Finance data. It
is not an official Yahoo product or an official real-time exchange feed.
The yfinance project describes this use as intended for personal research
and education; review Yahoo's terms for your use. Data availability, symbol
coverage, freshness, and statement labels can change. The app caches price
history briefly and reports longer-term statements from the upstream source.

For a production or public service, choose a market-data provider that grants
the required display and redistribution rights and supplies the freshness,
coverage, and intraday resolution you need. This workspace does not place
orders or connect to a brokerage.

Reference: [yfinance project and usage notes](https://github.com/ranaroussi/yfinance).
