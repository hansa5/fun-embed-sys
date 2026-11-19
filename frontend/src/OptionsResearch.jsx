import { useEffect, useMemo, useState } from 'react'
import './options-research.css'

const HELP = {
  delta: 'For a $1 share-price move, this estimates the option-price move per share if other inputs stay fixed. These are shown from the short-seller perspective.',
  gamma: 'How much delta may change after a $1 move in the share price. Short gamma is negative, so exposure can grow as the stock moves toward or through the strike.',
  rho: 'Estimated option-price change per share for a 1 percentage-point change in the interest-rate assumption. This matters more for longer expirations.',
  theta: 'Estimated option-price change per share for one calendar day passing, with other inputs fixed. Short options often have positive theta, but it is not a guaranteed daily gain.',
  vega: 'Estimated option-price change per share for a 1 percentage-point change in implied volatility. A short option has the opposite exposure to the long-option model value.',
  iv: 'Implied volatility is the movement scale reflected in this option’s price, calculated with a model. It does not say which direction the stock will move.',
  touch: 'Share of overlapping historical windows where the daily high or low crossed a strike at the same percentage distance from the window start. It is not an assignment probability.',
  finish: 'Share of historical windows where the final close was beyond a strike at the same percentage distance from the window start. This is not a forecast or assignment probability.',
}

const money = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value))
const percent = (value, digits = 1) => value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(digits)}%`
const rangePercent = (value, digits = 1) => value == null || !Number.isFinite(Number(value)) ? '—' : `±${Math.abs(Number(value)).toFixed(digits)}%`
const number = (value, digits = 3) => value == null || !Number.isFinite(Number(value)) ? '—' : Number(value).toFixed(digits)
const multiple = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(2)}×`
const spreadPct = (item) => item?.bid == null || item?.ask == null || (item.bid + item.ask) <= 0 ? null : ((item.ask - item.bid) / ((item.ask + item.bid) / 2)) * 100
const daysUntil = (value) => Math.max(0, Math.round((new Date(`${value}T00:00:00Z`) - new Date(`${new Date().toISOString().slice(0, 10)}T00:00:00Z`)) / 86400000))

function Tip({ name, children }) {
  return <span className="option-metric-label">{children}<details className="option-tip"><summary aria-label={`Explain ${children}`} title={HELP[name]}>i</summary><span>{HELP[name]}</span></details></span>
}

async function getJson(url) {
  const response = await fetch(url)
  const value = await response.json()
  if (!response.ok) throw new Error(value.detail || 'Options research is unavailable.')
  return value
}

export default function OptionsResearch() {
  const initialSymbol = new URLSearchParams(window.location.search).get('symbol') || 'AAPL'
  const [tickerInput, setTickerInput] = useState(initialSymbol)
  const [symbol, setSymbol] = useState(initialSymbol.toUpperCase())
  const [suggestions, setSuggestions] = useState([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [expirations, setExpirations] = useState([])
  const [expiration, setExpiration] = useState('')
  const [side, setSide] = useState('PUT')
  const [targetDays, setTargetDays] = useState('30')
  const [lookback, setLookback] = useState('5y')
  const [goal, setGoal] = useState('avoid')
  const [analysis, setAnalysis] = useState(null)
  const [earningsDate, setEarningsDate] = useState(null)
  const [selectedContract, setSelectedContract] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const query = tickerInput.trim()
    if (!query || !searchOpen) { setSuggestions([]); return undefined }
    let cancelled = false
    const timer = window.setTimeout(() => {
      fetch(`/api/market/search?q=${encodeURIComponent(query)}`).then((response) => response.ok ? response.json() : []).then((items) => { if (!cancelled) setSuggestions(items.slice(0, 6)) }).catch(() => { if (!cancelled) setSuggestions([]) })
    }, 150)
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [tickerInput, searchOpen])

  useEffect(() => {
    let cancelled = false
    setAnalysis(null); setExpiration(''); setExpirations([]); setError('')
    getJson(`/api/options/${encodeURIComponent(symbol)}`).then((market) => {
      if (cancelled) return
      const dates = market.expirations || []
      setExpirations(dates)
      if (!dates.length) { setError('No listed option expirations were returned for this ticker.'); return }
      const target = Number(targetDays) || 30
      const closest = dates.reduce((best, current) => Math.abs(daysUntil(current) - target) < Math.abs(daysUntil(best) - target) ? current : best, dates[0])
      setExpiration(closest)
    }).catch((reason) => { if (!cancelled) setError(reason.message) })
    return () => { cancelled = true }
  }, [symbol])

  useEffect(() => {
    let cancelled = false
    fetch(`/api/market/earnings?symbols=${encodeURIComponent(symbol)}`).then((response) => response.ok ? response.json() : []).then((items) => {
      if (!cancelled) setEarningsDate(items.find((item) => item.symbol === symbol)?.date || null)
    }).catch(() => { if (!cancelled) setEarningsDate(null) })
    return () => { cancelled = true }
  }, [symbol])

  useEffect(() => {
    if (!expiration) return undefined
    let cancelled = false
    setLoading(true); setError(''); setAnalysis(null)
    const query = new URLSearchParams({ expiration, option_type: side, lookback })
    getJson(`/api/options/${encodeURIComponent(symbol)}/research?${query}`).then((result) => {
      if (!cancelled) {
        setAnalysis(result)
        const first = result.contracts?.[0]
        const nearestOtm = (result.contracts || []).filter((item) => side === 'PUT' ? item.strike <= result.underlyingPrice : item.strike >= result.underlyingPrice).sort((a, b) => Math.abs(a.distancePct) - Math.abs(b.distancePct))[0]
        setSelectedContract((nearestOtm || first)?.contractSymbol || '')
      }
    }).catch((reason) => { if (!cancelled) setError(reason.message) }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol, expiration, side, lookback])

  const sortedContracts = useMemo(() => {
    const values = [...(analysis?.contracts || [])]
    values.sort((a, b) => {
      const left = a.historical?.finishInMoneyRate
      const right = b.historical?.finishInMoneyRate
      if (left == null && right != null) return 1
      if (right == null && left != null) return -1
      if (left != null && right != null && left !== right) return goal === 'avoid' ? left - right : right - left
      return Math.abs(a.distancePct) - Math.abs(b.distancePct)
    })
    return values
  }, [analysis, goal])
  const selected = sortedContracts.find((item) => item.contractSymbol === selectedContract) || sortedContracts[0]
  const targetExpiration = Number(targetDays) || 30
  const selectedDays = expiration ? daysUntil(expiration) : null
  const expirationOptions = expirations.map((value) => ({ value, days: daysUntil(value) }))

  function useTicker(value) {
    const normalized = value.trim().toUpperCase()
    if (!/^[A-Z0-9.-]{1,15}$/.test(normalized)) return
    setTickerInput(normalized); setSuggestions([]); setSearchOpen(false); setSymbol(normalized)
    const query = new URLSearchParams(window.location.search)
    query.set('options', '1'); query.set('symbol', normalized)
    window.history.replaceState({}, '', `${window.location.pathname}?${query.toString()}`)
  }

  function changeTargetDays(value) {
    setTargetDays(value)
    const target = Number(value)
    if (target > 0 && expirations.length) {
      const closest = expirations.reduce((best, current) => Math.abs(daysUntil(current) - target) < Math.abs(daysUntil(best) - target) ? current : best, expirations[0])
      setExpiration(closest)
    }
  }

  return <div className="options-research-page">
    <section className="options-research-heading"><div><div className="eyebrow">CONTRACT COMPARISON · HISTORICAL CONTEXT</div><h1>Options research</h1><p>Compare listed expirations and strikes using quote data, model Greeks, and historical price paths.</p></div></section>
    <div className="options-research-note"><b>No single contract is “optimal” for everyone.</b> Sort using your stated preference, inspect the evidence and risks, then decide. Historical touch and finish rates are not future probabilities or assignment odds.</div>
    <section className="options-controls panel">
      <label>TICKER<div className="options-ticker-search"><input value={tickerInput} onFocus={() => setSearchOpen(true)} onChange={(event) => { setTickerInput(event.target.value.toUpperCase()); setSearchOpen(true) }} onKeyDown={(event) => { if (event.key === 'Enter') useTicker(suggestions[0]?.symbol || tickerInput); if (event.key === 'Escape') { setSuggestions([]); setSearchOpen(false) } }} aria-label="Ticker" placeholder="e.g. AAPL" />{suggestions.length > 0 && <div className="options-suggestions">{suggestions.map((item) => <button type="button" key={item.symbol} onClick={() => useTicker(item.symbol)}><b>{item.symbol}</b><span>{item.name}</span></button>)}</div>}</div></label>
      <label>OPTION SIDE<select value={side} onChange={(event) => setSide(event.target.value)}><option value="PUT">Sell a put</option><option value="CALL">Sell a call</option></select></label>
      <label>TARGET DAYS<select value={targetDays} onChange={(event) => changeTargetDays(event.target.value)}><option value="14">14 days</option><option value="21">21 days</option><option value="30">30 days</option><option value="45">45 days</option><option value="60">60 days</option><option value="90">90 days</option></select></label>
      <label>LISTED EXPIRATION<select value={expiration} onChange={(event) => setExpiration(event.target.value)} disabled={!expirations.length}><option value="">Choose expiration</option>{expirationOptions.map((item) => <option key={item.value} value={item.value}>{item.value} · {item.days} days</option>)}</select></label>
      <label>PRICE HISTORY<select value={lookback} onChange={(event) => setLookback(event.target.value)}><option value="1y">1 year</option><option value="2y">2 years</option><option value="5y">5 years</option><option value="10y">10 years</option></select></label>
      <label>STRIKE SORT<select value={goal} onChange={(event) => setGoal(event.target.value)}><option value="avoid">Fewer historical finishes beyond strike</option><option value="accept">More historical finishes beyond strike</option></select></label>
    </section>
    {error && <div className="options-error">{error}</div>}
    {loading && <div className="options-loading">Loading option chain and {lookback} of daily price history…</div>}
    {analysis && <>
      <div className="options-data-line">{analysis.symbol} · Underlying {money(analysis.underlyingPrice)} · target {targetExpiration} days; selected expiration {analysis.expiration} ({analysis.daysToExpiration} days) · history through {analysis.historyDataDate} · retrieved {new Date(analysis.retrievedAt).toLocaleString()} · {analysis.source}</div>
      {earningsDate && earningsDate >= new Date().toISOString().slice(0, 10) && earningsDate <= analysis.expiration && <div className="options-event-warning"><b>Upcoming earnings date listed: {new Date(`${earningsDate}T00:00:00`).toLocaleDateString()}.</b> This event is inside the selected option's life and can cause a large price or volatility change. The date may be estimated; verify it with the company or your broker.</div>}
      <section className="options-summary-grid">
        <article><span>AVERAGE {analysis.daysToExpiration}-DAY RETURN</span><b>{percent(analysis.horizonReturns.averagePct)}</b></article>
        <article><span>LOWEST OBSERVED WINDOW RETURN</span><b className="option-risk">{percent(analysis.horizonReturns.minimumPct)}</b></article>
        <article><span>HIGHEST OBSERVED WINDOW RETURN</span><b className="option-upside">{percent(analysis.horizonReturns.maximumPct)}</b></article>
        <article><span>20-DAY HISTORICAL VOLATILITY</span><b>{percent(analysis.historicalVolatility20dPct)}</b><small>Annualized from recent daily returns</small></article>
        <article><span>60-DAY HISTORICAL VOLATILITY</span><b>{percent(analysis.historicalVolatility60dPct)}</b><small>Annualized from recent daily returns</small></article>
        <article><span>ROLLING WINDOWS</span><b>{analysis.sampleWindows.toLocaleString()}</b><small>Approx. {analysis.horizonSessions} trading sessions each</small></article>
      </section>
        <div className="options-history-explainer">The low/high figures are outcomes from overlapping historical windows, not limits on future moves. A gap can exceed the worst historical decline. For {side.toLowerCase()} strikes, the app rescales each old window to the same strike distance from its starting price. The table compares that gap with a rough one-standard-deviation move from recent historical volatility and from contract IV; neither is a boundary or a probability.</div>
      <section className="options-contract-section">
        <div className="options-section-heading"><div><span className="eyebrow">LISTED CONTRACTS</span><h2>{side === 'PUT' ? 'Put strikes' : 'Call strikes'}</h2></div><span>Sorted by historical end-window frequency for your selected goal</span></div>
        {sortedContracts.length === 0 ? <div className="options-empty">No contracts returned for this expiration.</div> : <div className="options-table-wrap"><table className="options-table"><thead><tr><th>Strike</th><th>Bid / ask</th><th>Distance</th><th><Tip name="iv">IV</Tip></th><th><Tip name="delta">Short Δ</Tip></th><th><Tip name="gamma">Short Γ</Tip></th><th><Tip name="rho">Short ρ</Tip></th><th><Tip name="touch">Historical touch</Tip></th><th><Tip name="finish">Finished beyond</Tip></th><th>Gap / HV move</th><th>Gap / IV move</th></tr></thead><tbody>{sortedContracts.map((item) => <tr key={item.contractSymbol} className={selected?.contractSymbol === item.contractSymbol ? 'options-row-selected' : ''} onClick={() => setSelectedContract(item.contractSymbol)} tabIndex="0" onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedContract(item.contractSymbol) } }}><td><b>{money(item.strike)}</b></td><td>{item.bid == null || item.ask == null ? '—' : `${money(item.bid)} / ${money(item.ask)}`}<small>mark {money(item.mark)}</small></td><td className={item.distancePct >= 0 ? 'option-risk' : 'option-upside'}>{percent(item.distancePct, 2)}</td><td>{percent(item.impliedVolatility == null ? null : item.impliedVolatility * 100)}</td><td>{number(item.greeks ? -item.greeks.delta : null)}</td><td>{number(item.greeks ? -item.greeks.gamma : null, 5)}</td><td>{number(item.greeks ? -item.greeks.rhoPerRatePoint : null, 4)}</td><td>{percent(item.historical?.touchRate == null ? null : item.historical.touchRate * 100)}<small>{item.historical?.windows || 0} windows</small></td><td>{percent(item.historical?.finishInMoneyRate == null ? null : item.historical.finishInMoneyRate * 100)}</td><td>{multiple(item.distanceInHistoricalMoves)}</td><td>{multiple(item.distanceInImpliedMoves)}</td></tr>)}</tbody></table></div>}
      </section>
      {selected && <section className="options-selected panel"><div className="options-section-heading"><div><span className="eyebrow">SELECTED FOR REVIEW</span><h2>{analysis.symbol} {side} {money(selected.strike)} · {analysis.expiration}</h2></div><span>{selectedDays} days to expiration</span></div>
        <div className="options-selected-grid"><div><small>STRIKE GAP</small><b>{percent(selected.distancePct, 2)} from share price</b></div><div><small>OPTION-ONLY SHORT BREAK-EVEN</small><b>{money(selected.breakEven)}</b></div><div><small>BID / ASK</small><b>{money(selected.bid)} / {money(selected.ask)}</b></div><div><small>BID / ASK SPREAD AS % OF MARK</small><b>{percent(spreadPct(selected), 2)}</b></div><div><small>VOLUME / OPEN INTEREST</small><b>{number(selected.volume, 0)} / {number(selected.openInterest, 0)}</b></div><div><small>MODEL IV</small><b>{percent(selected.impliedVolatility == null ? null : selected.impliedVolatility * 100)}</b></div><div><small>APPROX 1σ MOVE · CONTRACT IV</small><b>{rangePercent(selected.impliedExpectedMovePct, 2)}</b></div><div><small>GAP / IV-BASED 1σ MOVE</small><b>{multiple(selected.distanceInImpliedMoves)}</b></div><div><small>APPROX 1σ MOVE · RECENT HV</small><b>{rangePercent(selected.historicalExpectedMovePct, 2)}</b></div><div><small>GAP / HISTORICAL 1σ MOVE</small><b>{multiple(selected.distanceInHistoricalMoves)}</b></div><div><small>EST. HISTORICAL TOUCH</small><b>{percent(selected.historical?.touchRate == null ? null : selected.historical.touchRate * 100)}</b></div><div><small>EST. HISTORICAL FINISH BEYOND</small><b>{percent(selected.historical?.finishInMoneyRate == null ? null : selected.historical.finishInMoneyRate * 100)}</b></div><div><small>AVG MOVE TOWARD THIS STRIKE</small><b>{percent(selected.historical?.averageMoveTowardStrikePct)}</b></div><div><small>LARGEST HISTORICAL MOVE TOWARD STRIKE</small><b>{percent(selected.historical?.worstMoveTowardStrikePct)}</b></div></div>
        <div className="options-greeks-title">Approximate short-option sensitivities <span>per share · multiply by 100 for one contract</span></div>
        <div className="options-greek-grid">{[['delta','Short delta',selected.greeks ? -selected.greeks.delta : null],['gamma','Short gamma',selected.greeks ? -selected.greeks.gamma : null],['theta','Short theta / day',selected.greeks ? -selected.greeks.thetaPerDay : null],['vega','Short vega / IV point',selected.greeks ? -selected.greeks.vegaPerVolPoint : null],['rho','Short rho / rate point',selected.greeks ? -selected.greeks.rhoPerRatePoint : null]].map(([key,label,value]) => <div key={key}><Tip name={key}>{label}</Tip><b>{number(value, key === 'gamma' ? 5 : 4)}</b></div>)}</div>
        <div className="options-model-note">{analysis.greeksModel}. Rate input: {analysis.riskFreeRatePct == null ? 'unavailable; Greeks omitted' : `${analysis.riskFreeRatePct.toFixed(2)}% 13-week Treasury proxy as of ${analysis.riskFreeRateDate}`}; trailing dividend-yield estimate {percent(analysis.trailingDividendYieldPct)}. These are European-model approximations; U.S. single-stock options are American-style. Check live quotes and dividends with your broker.</div>
      </section>}
    </>}
  </div>
}
