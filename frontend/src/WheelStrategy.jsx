import { useCallback, useEffect, useMemo, useState } from 'react'

const money = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value))
const prettyDate = (value) => value ? new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'
const stateLabels = {
  PUT_OPEN: 'Short put open', PUT_CASH_READY: 'Cash ready · next put', SHARES_HELD: 'Shares held · covered call',
  CALL_OPEN: 'Covered call open', CLOSED: 'Cycle closed',
}

async function api(url, options) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'The wheel tracker request failed.')
  return body
}

function ContractPicker({ symbol, type, onValues, compact = false }) {
  const [market, setMarket] = useState(null)
  const [expiration, setExpiration] = useState('')
  const [strike, setStrike] = useState('')
  const [contracts, setContracts] = useState('1')
  const [premium, setPremium] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const chain = type === 'PUT' ? market?.puts || [] : market?.calls || []
  const selected = chain.find((item) => String(item.strike) === strike)

  useEffect(() => {
    let cancelled = false
    setMarket(null); setError(''); setExpiration(''); setStrike(''); setPremium('')
    if (!symbol || !/^[A-Z0-9.-]{1,15}$/.test(symbol)) return undefined
    setLoading(true)
    const timer = window.setTimeout(() => {
      api(`/api/options/${encodeURIComponent(symbol)}`)
        .then((result) => { if (!cancelled) { setMarket(result); setExpiration(result.expiration || '') } })
        .catch((reason) => { if (!cancelled) setError(reason.message) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, 300)
    return () => { cancelled = true; window.clearTimeout(timer) }
  }, [symbol])

  useEffect(() => {
    let cancelled = false
    if (!symbol || !expiration) return undefined
    setLoading(true); setError('')
    api(`/api/options/${encodeURIComponent(symbol)}?expiration=${encodeURIComponent(expiration)}`)
      .then((result) => { if (!cancelled) { setMarket(result); setStrike('') } })
      .catch((reason) => { if (!cancelled) setError(reason.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [symbol, expiration])

  useEffect(() => {
    onValues({ strike, expiration, contracts, premium, selected })
  }, [strike, expiration, contracts, premium, selected?.contractSymbol])

  return <div className={`contract-picker ${compact ? 'contract-picker-compact' : ''}`}>
    <div className="wheel-form-grid">
      <label>EXPIRATION<select value={expiration} onChange={(event) => setExpiration(event.target.value)} disabled={!market?.expirations?.length}><option value="">Choose date</option>{market?.expirations?.map((item) => <option key={item} value={item}>{prettyDate(item)}</option>)}</select></label>
      <label>{type} STRIKE<select value={strike} onChange={(event) => setStrike(event.target.value)} disabled={!chain.length}><option value="">Choose strike</option>{chain.map((item) => <option key={item.contractSymbol} value={item.strike}>{money(item.strike)} · bid {money(item.bid)} / ask {money(item.ask)}</option>)}</select></label>
      <label>CONTRACTS<input type="number" min="1" step="1" value={contracts} onChange={(event) => setContracts(event.target.value)} /></label>
      <label>ACTUAL CREDIT / SHARE<input type="number" min="0" step="0.01" placeholder="Your fill" value={premium} onChange={(event) => setPremium(event.target.value)} /></label>
    </div>
    <div className="contract-quote-line">{loading ? 'Loading option quotes…' : market?.underlyingPrice != null ? `${symbol} ${money(market.underlyingPrice)} · selected ${selected ? `bid ${money(selected.bid)} / ask ${money(selected.ask)}` : 'no contract selected'}` : selected ? `bid ${money(selected.bid)} / ask ${money(selected.ask)}` : 'Select an expiration and strike. Enter your actual execution credit.'}{error && <span className="wheel-inline-error">{error}</span>}</div>
  </div>
}

function WheelStrategy() {
  const [cycles, setCycles] = useState([])
  const [analysis, setAnalysis] = useState({})
  const [selectedId, setSelectedId] = useState('')
  const [selectedDetails, setSelectedDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [mode, setMode] = useState('put')
  const [symbol, setSymbol] = useState('AAPL')
  const [shares, setShares] = useState('100')
  const [basis, setBasis] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [maxLoss, setMaxLoss] = useState('')
  const [expiryDays, setExpiryDays] = useState('7')
  const [newLeg, setNewLeg] = useState({})
  const [actionLeg, setActionLeg] = useState({})
  const [actionForm, setActionForm] = useState('')
  const [closePrice, setClosePrice] = useState('')
  const [saleShares, setSaleShares] = useState('')
  const [salePrice, setSalePrice] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const refresh = useCallback(async () => {
    setError('')
    try {
      const items = await api('/api/wheel')
      setCycles(items)
      setSelectedId((current) => current && items.some((item) => item.id === current) ? current : items[0]?.id || '')
    } catch (reason) { setError(reason.message) } finally { setLoading(false) }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const timer = window.setInterval(refresh, 60000)
    return () => window.clearInterval(timer)
  }, [refresh])

  useEffect(() => {
    let cancelled = false
    const open = cycles.filter((item) => item.activeLeg)
    if (!open.length) { setAnalysis({}); return undefined }
    Promise.all(open.map(async (item) => {
      try { return [item.id, await api(`/api/wheel/${item.id}/analysis`)] }
      catch (reason) { return [item.id, { alerts: [{ level: 'info', message: reason.message }], marketAvailable: false }] }
    })).then((entries) => { if (!cancelled) setAnalysis(Object.fromEntries(entries)) })
    return () => { cancelled = true }
  }, [cycles])

  useEffect(() => {
    let cancelled = false
    if (!selectedId) { setSelectedDetails(null); return undefined }
    api(`/api/wheel/${selectedId}`).then((data) => { if (!cancelled) setSelectedDetails(data) }).catch((reason) => { if (!cancelled) setError(reason.message) })
    return () => { cancelled = true }
  }, [selectedId, cycles])

  const selected = useMemo(() => cycles.find((item) => item.id === selectedId) || null, [cycles, selectedId])


  async function submitNew(event) {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const payload = { symbol, startMode: mode, takeProfitPercent: takeProfit || null, maxLossDollars: maxLoss || null, expiryAlertDays: expiryDays }
      if (mode === 'put') Object.assign(payload, newLeg)
      else Object.assign(payload, { shares, shareCostBasis: basis })
      const created = await api('/api/wheel', { method: 'POST', body: JSON.stringify(payload) })
      await refresh(); setSelectedId(created.id); setShowNew(false); setTakeProfit(''); setMaxLoss(''); setBasis('')
    } catch (reason) { setError(reason.message) } finally { setSubmitting(false) }
  }

  async function doAction(action, payload = {}) {
    if (!selected) return
    setSubmitting(true); setError('')
    try {
      await api(`/api/wheel/${selected.id}/actions/${action}`, { method: 'POST', body: JSON.stringify(payload) })
      setActionLeg({})
      await refresh(); setActionForm(''); setClosePrice(''); setSaleShares(''); setSalePrice('')
    } catch (reason) { setError(reason.message) } finally { setSubmitting(false) }
  }

  async function openLeg(action, values) {
    const payload = { strike: values.strike, expiration: values.expiration, contracts: values.contracts, premium: values.premium }
    await doAction(action, payload)
  }

  const selectedAnalysis = selected ? analysis[selected.id] : null

  return <div className="wheel-page">
    <section className="analysis-heading wheel-heading">
      <div><div className="eyebrow">OPTIONS WORKSPACE <span>·</span> TRACK EVERY LEG</div><h1>Wheel strategy</h1><p>Track cash-secured puts, assignment, covered calls, closes, and the next cycle.</p></div>
      <button className="wheel-primary-button" onClick={() => { setMode('put'); setSymbol('AAPL'); setShowNew((open) => !open) }}>{showNew ? 'Cancel new cycle' : '+ New wheel cycle'}</button>
    </section>

    <div className="wheel-disclaimer"><b>Research tracker, not trade execution.</b> Quote data can be delayed or incomplete. Assignment is determined by your broker; confirm the actual outcome before recording it. Alerts apply only to the thresholds you set.</div>
    {error && <div className="wheel-error">{error}</div>}

    {showNew && <section className="panel wheel-panel new-wheel-panel">
      <div className="wheel-panel-heading"><div><span className="panel-kicker">CREATE A TRACKED INSTANCE</span><h2>Start a wheel cycle</h2></div></div>
      <form className="wheel-form" onSubmit={submitNew}>
        <div className="wheel-form-grid">
          <label>TICKER<input value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} required maxLength="15" /></label>
          <label>STARTING POINT<select value={mode} onChange={(event) => setMode(event.target.value)}><option value="put">Sell a cash-secured put</option><option value="shares">I already own shares</option></select></label>
        </div>
        {mode === 'put' ? <ContractPicker key={`${symbol}-PUT-new`} symbol={symbol} type="PUT" onValues={setNewLeg} /> : <div className="wheel-form-grid"><label>SHARES OWNED<input type="number" min="1" step="1" value={shares} onChange={(event) => setShares(event.target.value)} /></label><label>AVERAGE COST / SHARE<input type="number" min="0.01" step="0.01" value={basis} onChange={(event) => setBasis(event.target.value)} placeholder="Your recorded cost" /></label></div>}
        <div className="wheel-form-grid wheel-alert-inputs">
          <label>PROFIT-CAPTURE ALERT % <input type="number" min="1" max="99.9" step="0.1" value={takeProfit} onChange={(event) => setTakeProfit(event.target.value)} placeholder="Optional" /></label>
          <label>LOSS ALERT $ <input type="number" min="0.01" step="0.01" value={maxLoss} onChange={(event) => setMaxLoss(event.target.value)} placeholder="Optional" /></label>
          <label>EXPIRY ALERT · DAYS <input type="number" min="0" step="1" value={expiryDays} onChange={(event) => setExpiryDays(event.target.value)} /></label>
        </div>
        <div className="wheel-form-note">Optional alerts are user-set thresholds; blank thresholds are not guessed for you. Option bid/ask is context only—enter your actual premium fill.</div>
        <button className="wheel-primary-button" disabled={submitting || (mode === 'put' && (!newLeg.strike || !newLeg.premium || !newLeg.expiration))}>{submitting ? 'Saving…' : 'Create cycle'}</button>
      </form>
    </section>}

    <div className="wheel-layout">
      <section className="wheel-cycle-list">
        <div className="wheel-list-heading"><div><span className="panel-kicker">YOUR TRACKED POSITIONS</span><h2>Wheel instances</h2></div><button className="wheel-quiet-button" onClick={refresh}>Refresh</button></div>
        {loading ? <div className="table-loading"><span className="loader" />Loading tracked cycles…</div> : cycles.length === 0 ? <div className="panel wheel-empty">No wheel cycles yet. Start with a put or record shares you already own.</div> : cycles.map((item) => <button key={item.id} className={`wheel-cycle-card ${selectedId === item.id ? 'wheel-cycle-selected' : ''}`} onClick={() => setSelectedId(item.id)}>
          <span className="wheel-cycle-top"><b>{item.symbol}</b><i>{stateLabels[item.state] || item.state}</i></span>
          <span className="wheel-cycle-sub">{item.activeLeg ? `${item.activeLeg.type} ${money(item.activeLeg.strike)} · ${prettyDate(item.activeLeg.expiration)}` : `${item.shares} shares · ${money(item.shareCostBasis)} basis`}</span>
          <span className={`wheel-pnl ${item.realizedPnl >= 0 ? 'wheel-positive' : 'wheel-negative'}`}>Realized {money(item.realizedPnl)}</span>
        </button>)}
      </section>

      <section className="wheel-detail-column">
        {!selected ? <div className="panel wheel-empty">Choose a wheel cycle to see its current state and history.</div> : <>
          <section className="panel wheel-panel wheel-state-panel">
            <div className="wheel-panel-heading"><div><span className="panel-kicker">{selected.symbol} · CURRENT STATE</span><h2>{stateLabels[selected.state] || selected.state}</h2></div><span className="wheel-state-pill">{selected.state.replaceAll('_', ' ')}</span></div>
            {selected.activeLeg ? <>
              <div className="wheel-position-grid">
                <div><small>OPEN LEG</small><b>Short {selected.activeLeg.type}</b></div>
                <div><small>STRIKE</small><b>{money(selected.activeLeg.strike)}</b></div>
                <div><small>EXPIRATION</small><b>{prettyDate(selected.activeLeg.expiration)}</b></div>
                <div><small>CONTRACTS</small><b>{selected.activeLeg.contracts}</b></div>
                <div><small>ENTRY CREDIT</small><b>{money(selected.activeLeg.premium)} / share</b></div>
                <div><small>MAX PUT COLLATERAL</small><b>{selected.activeLeg.type === 'PUT' ? money(selected.activeLeg.strike * 100 * selected.activeLeg.contracts) : 'Covered by shares'}</b></div>
              </div>
              <div className="wheel-analysis-box">
                <div className="wheel-analysis-title"><b>Market checks</b><span>{selectedAnalysis?.marketAvailable ? 'Yahoo Finance · refreshed every minute' : 'Waiting for option quote'}</span></div>
                {selectedAnalysis?.underlyingPrice != null && <div className="wheel-market-metrics"><span>Underlying <b>{money(selectedAnalysis.underlyingPrice)}</b></span><span>Option mark <b>{money(selectedAnalysis.optionMark)}</b></span><span>Open P&amp;L <b className={(selectedAnalysis.unrealizedPnl || 0) >= 0 ? 'wheel-positive' : 'wheel-negative'}>{money(selectedAnalysis.unrealizedPnl)}</b></span><span>Captured <b>{selectedAnalysis.premiumCapturedPercent == null ? '—' : `${selectedAnalysis.premiumCapturedPercent.toFixed(0)}%`}</b></span><span>Break-even at expiry <b>{money(selectedAnalysis.breakEvenAtExpiration)}</b></span>{selectedAnalysis.coveredCallAssignmentPnl != null && <span>If assigned <b className={selectedAnalysis.coveredCallAssignmentPnl >= 0 ? 'wheel-positive' : 'wheel-negative'}>{money(selectedAnalysis.coveredCallAssignmentPnl)}</b></span>}<span>Days left <b>{selectedAnalysis.daysToExpiration}</b></span></div>}
                <p>{selectedAnalysis?.nextScenarios || (selected.activeLeg.type === 'PUT' ? 'If OTM at expiry: cash-ready for another put. If assigned: shares-held, then covered calls.' : 'If OTM at expiry: keep shares and consider the next call. If assigned: shares are called away and the cycle returns to puts.')}</p>
                {selectedAnalysis?.alerts?.length > 0 && <div className="wheel-alert-list">{selectedAnalysis.alerts.map((alert, index) => <div key={`${alert.code || alert.message}-${index}`} className={`wheel-alert wheel-alert-${alert.level}`}><span>{alert.level === 'risk' ? '!' : alert.level === 'action' ? '●' : '·'}</span>{alert.message}</div>)}</div>}
                <small className="wheel-data-note">{selectedAnalysis?.dataSource || 'Underlying and option quotes may be delayed, incomplete, or unavailable. No orders are placed.'}</small>
              </div>
              <div className="wheel-actions">
                {actionForm === 'close' ? <div className="wheel-inline-form"><label>BUY-TO-CLOSE PRICE / SHARE<input type="number" min="0" step="0.01" value={closePrice} onChange={(event) => setClosePrice(event.target.value)} /></label><button className="wheel-primary-button" disabled={submitting || closePrice === ''} onClick={() => doAction('close_option', { closePrice })}>Record close</button><button className="wheel-quiet-button" onClick={() => setActionForm('')}>Cancel</button></div> : <button className="wheel-secondary-button" onClick={() => setActionForm('close')}>Record buy-to-close</button>}
                <button className="wheel-secondary-button" disabled={submitting} onClick={() => doAction('expire_otm')}>Record expired OTM</button>
                <button className="wheel-secondary-button" disabled={submitting} onClick={() => doAction('assigned')}>Record assignment</button>
              </div>
            </> : <div className="wheel-position-grid wheel-holding-grid"><div><small>SHARES HELD</small><b>{selected.shares}</b></div><div><small>ECONOMIC BASIS / SHARE</small><b>{money(selected.shareCostBasis)}</b></div><div><small>REALIZED P&amp;L</small><b>{money(selected.realizedPnl)}</b></div><div><small>STATE</small><b>{selected.state === 'PUT_CASH_READY' ? 'No shares or open option' : 'Shares recorded'}</b></div></div>}
          </section>

          {selected.state === 'PUT_CASH_READY' && <section className="panel wheel-panel"><div className="wheel-panel-heading"><div><span className="panel-kicker">NEXT LOOP</span><h2>Sell another put</h2></div></div><ContractPicker key={`${selected.id}-PUT-${selected.updatedAt}`} symbol={selected.symbol} type="PUT" compact onValues={setActionLeg} /><div className="wheel-form-actions"><button className="wheel-primary-button" disabled={submitting || !actionLeg.strike || !actionLeg.premium || !actionLeg.expiration} onClick={() => openLeg('sell_put', actionLeg)}>Record put sale</button><button className="wheel-quiet-button" disabled={submitting} onClick={() => doAction('close_cycle')}>Close cycle</button></div></section>}
          {selected.state === 'SHARES_HELD' && <>
            <section className="panel wheel-panel"><div className="wheel-panel-heading"><div><span className="panel-kicker">COVERED-CALL STAGE</span><h2>Sell a covered call</h2></div><span className="wheel-call-cover">{Math.floor(selected.shares / 100)} contracts covered</span></div><ContractPicker key={`${selected.id}-CALL-${selected.updatedAt}`} symbol={selected.symbol} type="CALL" compact onValues={setActionLeg} /><div className="wheel-form-actions"><button className="wheel-primary-button" disabled={submitting || !actionLeg.strike || !actionLeg.premium || !actionLeg.expiration || Number(actionLeg.contracts) * 100 > selected.shares} onClick={() => openLeg('sell_call', actionLeg)}>Record call sale</button></div></section>
            <section className="panel wheel-panel"><div className="wheel-panel-heading"><div><span className="panel-kicker">OPTIONAL MANUAL CLOSE</span><h2>Sell shares</h2></div></div><div className="wheel-inline-form"><label>SHARES TO SELL<input type="number" min="1" max={selected.shares} step="1" value={saleShares} onChange={(event) => setSaleShares(event.target.value)} /></label><label>SALE PRICE / SHARE<input type="number" min="0" step="0.01" value={salePrice} onChange={(event) => setSalePrice(event.target.value)} /></label><button className="wheel-secondary-button" disabled={submitting || !saleShares || !salePrice} onClick={() => doAction('sell_shares', { shares: saleShares, price: salePrice })}>Record share sale</button></div></section>
          </>}

          <section className="panel wheel-panel wheel-history-panel"><div className="wheel-panel-heading"><div><span className="panel-kicker">AUDIT TRAIL</span><h2>State transitions</h2></div></div>{selectedDetails?.events?.length ? <div className="wheel-event-list">{selectedDetails.events.map((event) => <div key={event.id} className="wheel-event"><span className="wheel-event-dot" /><div><b>{event.type.replaceAll('_', ' ')}</b><small>{event.fromState?.replaceAll('_', ' ') || 'Start'} → {event.toState.replaceAll('_', ' ')}</small></div><time>{new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(event.createdAt))}</time></div>)}</div> : <div className="wheel-form-note">No recorded transitions yet.</div>}</section>
        </>}
      </section>
    </div>
    <div className="wheel-footer-note">Strategy results depend on the underlying price, option liquidity, early exercise, contract assignment, taxes, commissions, and corporate actions. The tracker records your actions; it does not connect to a brokerage or tell you which trade to place.</div>
  </div>
}

export default WheelStrategy
