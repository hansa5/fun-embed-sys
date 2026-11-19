# Options research: strikes, expirations, volatility, and Greeks

Options Research compares listed contracts for a ticker and side. Choose a target number of calendar days, then select a listed expiration near that target. The app sorts contracts by historical end-of-window frequency according to the selected goal (lower for fewer historical finishes beyond the strike, higher when exploring strikes that finished beyond it more often). This is a research filter, not an optimal-contract picker or a forecast.

## Strike distance and historical price paths

- **Strike distance** is `(strike / current share price − 1) × 100`. A put strike below the current price has a negative distance; a call strike above it has a positive distance.
- **Historical horizon return** compares the close at the start of each rolling window with the close at its end. The page reports the average, lowest, and highest observed window return over the selected lookback.
- **Historical touch frequency** counts how often the daily low crossed a put strike, or the daily high crossed a call strike, at the same percentage distance from the start price. A touch can reverse before expiration.
- **Historical finish beyond strike** counts how often the closing price at the end of a window was below a put strike or above a call strike at that same relative distance.
- Windows overlap, so their observations are not independent. The data are historical examples, not the probability of future assignment. Actual assignment is determined through the clearing and broker process; early exercise, after-hours prices, and expiration handling can matter.
- **Historical volatility (HV)** describes price movement measured from past prices. **Implied volatility (IV)** is backed out from the selected option's current price using a model. It reflects the market's priced-in scale of possible movement, not direction. They answer different questions and can differ substantially. [OIC: Volatility & the Greeks](https://www.optionseducation.org/advancedconcepts/volatility-the-greeks)
- The page annualizes the standard deviation of recent daily log returns over 20 and 60 trading sessions. It scales 20-session HV and each contract's IV by the square root of time to show an approximate one-standard-deviation move. The strike gap divided by that move is a comparison aid; it is not a probability or a price boundary.

The selected contract's historical touch and finish counts use a rolling horizon converted from calendar days to an approximate number of trading sessions. Daily highs/lows cannot reveal the exact intraday path. The historical summary therefore should not be read as a precise barrier probability or assignment estimate.

## Greeks, in plain language

The Options Research table shows model-estimated Greeks for a **long option**. A short option has the opposite signs for these sensitivities. Values are per share; multiply by 100 for an approximate one-contract sensitivity. They are model guideposts, not guaranteed premium changes.

- **Delta (Δ):** approximate option price change for a $1 move in the share price, holding other inputs fixed. A call delta is usually positive; a put delta is usually negative.
- **Gamma (Γ):** how much delta changes for a $1 share-price move. Gamma tends to be larger near the strike and close to expiration, so delta can change quickly.
- **Theta (Θ):** approximate option price change for one calendar day passing, with other inputs fixed. Long-option theta is often negative; a short option has the opposite exposure. Theta is not constant.
- **Vega:** approximate option price change for a one-percentage-point change in implied volatility. Higher IV generally raises both call and put premiums, all else equal.
- **Rho (ρ):** approximate option price change for a one-percentage-point change in the interest-rate assumption. It tends to matter more for longer expirations than near-term contracts.

The app calculates Greeks with a Black–Scholes European-style approximation using the selected contract IV, a 13-week Treasury-yield proxy, and a trailing dividend-yield estimate. U.S. single-stock options are American-style; this model does not model early exercise, discrete dividend dates, volatility skew mechanics, or all market microstructure effects. Rho and the other displayed Greeks are consequently rough context, not the broker's Greeks. See [OIC: Understanding Options Greeks](https://prd-web.optionseducation.org/advancedconcepts/understanding-options-greeks) and the [OCC Options Disclosure Document](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document).

## How to use the view

1. Select a ticker, put or call, target days to expiration, and historical lookback.
2. Review the nearest available listed expiration and choose another expiration if desired.
3. Compare strike distance, bid/ask, IV, Greeks, historical touch frequency, and historical finish-beyond-strike frequency.
4. Decide whether the position's cash or share exposure fits your plan. For a put, consider whether you are willing and able to buy shares at the strike. For a covered call, consider whether you are willing to sell the shares there and how that interacts with your share cost basis and an upcoming dividend.
5. Confirm the live quote, open interest, dividend/ex-dividend details, and assignment terms at your broker before placing an order. Quotes accessed through this app can be delayed or incomplete.

The view does not account for taxes, commissions, slippage, the exact executable fill, all corporate actions, or the user's portfolio concentration. It does not place orders.
