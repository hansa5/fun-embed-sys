import { useCallback, useEffect, useMemo, useState } from 'react'
import './market-radar.css'

const pct = (value) => value == null ? '—' : `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`
const price = (value) => value == null ? '—' : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(value)

export default function MarketRadar({ onSelectTicker }) {
  const [data, setData] = useState({ run: null, items: [] })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [watchlist, setWatchlist] = useState([])
  const [tickerInput, setTickerInput] = useState('')
  const load = useCallback(async () => {
    try {
      const response = await fetch('/api/market/radar')
      if (!response.ok) throw new Error('Could not load the saved radar scan.')
      setData(await response.json())
      const watchResponse = await fetch('/api/market/radar/watchlist')
      if (watchResponse.ok) setWatchlist(await watchResponse.json())
      setError('')
    } catch (reason) { setError(reason.message) }
  }, [])
  useEffect(() => { load() }, [load])
  const scan = async () => {
    setBusy(true)
    setError('')
    try {
      const response = await fetch('/api/market/radar/scan', { method: 'POST' })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Market scan failed.')
      await load()
    } catch (reason) { setError(reason.message) } finally { setBusy(false) }
  }
  const addTicker = async (event) => {
    event.preventDefault()
    const symbol = tickerInput.trim().toUpperCase()
    if (!/^[A-Z0-9.-]{1,15}$/.test(symbol)) return
    try {
      const response = await fetch('/api/market/radar/watchlist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol }) })
      const result = await response.json()
      if (!response.ok) throw new Error(result.detail || 'Could not add ticker.')
      setWatchlist((items) => [...items.filter((item) => item.symbol !== result.symbol), result].sort((a, b) => a.symbol.localeCompare(b.symbol)))
      setTickerInput('')
    } catch (reason) { setError(reason.message) }
  }
  const removeTicker = async (symbol) => {
    try {
      const response = await fetch(`/api/market/radar/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Could not remove ticker from your watchlist.')
      setWatchlist((items) => items.filter((item) => item.symbol !== symbol))
    } catch (reason) { setError(reason.message) }
  }
  const movers = useMemo(() => [...data.items].sort((a, b) => (b.return1d ?? -Infinity) - (a.return1d ?? -Infinity)), [data.items])
  const candidates = useMemo(() => [...data.items].sort((a, b) => b.trendScore - a.trendScore || (b.relativeStrength20d ?? -Infinity) - (a.relativeStrength20d ?? -Infinity)), [data.items])
  const updated = data.run?.scannedAt ? new Date(data.run.scannedAt).toLocaleString() : 'No scan yet'
  return <div className="radar-page">
    <section className="radar-heading"><div><div className="eyebrow">MARKET RESEARCH · DAILY PRICE DATA</div><h1>Market radar</h1><p>Find notable price moves and review a small set of transparent trend signals.</p></div><button className="radar-scan" onClick={scan} disabled={busy}>{busy ? 'Scanning…' : 'Run scan'}</button></section>
    <div className="radar-note"><b>Research context only.</b> The trend score counts historical conditions; it is not a forecast, probability, or buy/sell recommendation. Quotes and history may be delayed or incomplete. Source: {data.source || 'Yahoo Finance via yfinance'}.</div>
    <form className="radar-watchlist" onSubmit={addTicker}><label htmlFor="radar-ticker">Add a ticker to your saved scan universe</label><div><input id="radar-ticker" value={tickerInput} onChange={(event) => setTickerInput(event.target.value.toUpperCase())} placeholder="e.g. QCOM" maxLength="15" /><button disabled={!/^[A-Z0-9.-]{1,15}$/.test(tickerInput.trim())}>Add ticker</button></div><small>Saved in SQLite; included in manual and scheduled scans.</small>{watchlist.length > 0 && <div className="radar-watch-tags">{watchlist.map((item) => <span key={item.symbol}>{item.symbol}<button type="button" aria-label={`Remove ${item.symbol}`} onClick={() => removeTicker(item.symbol)}>×</button></span>)}</div>}</form>
    <div className="radar-meta">Latest scan: {updated}{data.run?.marketDate ? ` · Latest market data: ${data.run.marketDate}` : ''}{data.run ? ` · ${data.run.successCount}/${data.run.universeCount} symbols` : ''}</div>
    {error && <div className="radar-error">{error}</div>}
    {!data.run && !error && <div className="radar-empty">Run the first scan to build your market overview.</div>}
    {data.run && <>
      <section className="radar-section"><div className="radar-section-title"><div><span className="eyebrow">PRICE ACTION</span><h2>Top movers</h2></div><small>Daily close changes</small></div><div className="radar-movers">
        {[...movers.slice(0, 5), ...movers.slice(-5).reverse()].filter((item, index, list) => list.findIndex((candidate) => candidate.symbol === item.symbol) === index).map((item) => <button className="radar-mover" key={item.symbol} onClick={() => onSelectTicker(item.symbol)}><span className="radar-ticker">{item.symbol}</span><span className="radar-mover-price">{price(item.close)}</span><b className={item.return1d >= 0 ? 'up' : 'down'}>{pct(item.return1d)}</b></button>)}
      </div></section>
      <section className="radar-section"><div className="radar-section-title"><div><span className="eyebrow">RULE BASED FILTER</span><h2>Research candidates</h2></div><small>Sorted by trend alignment, then relative strength</small></div>
        <div className="radar-table-wrap"><table className="radar-table"><thead><tr><th>Company</th><th>Close</th><th>1 day</th><th>5 days</th><th>20 days</th><th>Relative vs SPY</th><th>Trend checks</th><th>Context</th></tr></thead><tbody>{candidates.map((item) => <tr key={item.symbol}><td><button className="radar-symbol" onClick={() => onSelectTicker(item.symbol)}>{item.symbol}<small>{item.name}</small></button></td><td>{price(item.close)}</td><td className={item.return1d >= 0 ? 'up' : 'down'}>{pct(item.return1d)}</td><td className={item.return5d >= 0 ? 'up' : 'down'}>{pct(item.return5d)}</td><td className={item.return20d >= 0 ? 'up' : 'down'}>{pct(item.return20d)}</td><td className={item.relativeStrength20d >= 0 ? 'up' : 'down'}>{pct(item.relativeStrength20d)}</td><td><span className="radar-score">{item.trendScore}/4</span><small className="radar-evidence">{item.evidence.filter((entry) => entry.passed).map((entry) => entry.label.replace(' over 20 days', '').replace('Price above ', '> ')).join(' · ') || 'No checks currently pass'}</small></td><td>{item.setup}</td></tr>)}</tbody></table></div>
      </section>
      {data.run.errors?.length > 0 && <details className="radar-errors"><summary>{data.run.errorCount} symbols unavailable</summary><ul>{data.run.errors.map((item) => <li key={item}>{item}</li>)}</ul></details>}
    </>}
  </div>
}
