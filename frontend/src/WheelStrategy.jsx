import { useCallback, useEffect, useMemo, useState } from 'react'

const money = (value) => value == null || !Number.isFinite(Number(value)) ? '—' : new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(Number(value))
const prettyDate = (value) => value ? new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'
const stateLabels = {
  PUT_OPEN: 'Short put open', PUT_CASH_READY: 'Cash ready · next put', SHARES_HELD: 'Shares held · covered call',
  CALL_OPEN: 'Covered call open', CLOSED: 'Cycle closed',
}
const DEFAULT_TICKERS = [
  ['AAPL', 'Apple'], ['GOOGL', 'Alphabet'], ['TSLA', 'Tesla'], ['NVDA', 'NVIDIA'],
  ['PGR', 'Progressive'], ['QCOM', 'Qualcomm'], ['MSFT', 'Microsoft'], ['META', 'Meta'],
  ['AMZN', 'Amazon'], ['BAC', 'Bank of America'], ['AVGO', 'Broadcom'], ['ORCL', 'Oracle'],
  ['AMD', 'AMD'], ['INTC', 'Intel'], ['NFLX', 'Netflix'], ['ADBE', 'Adobe'],
  ['CRM', 'Salesforce'], ['IBM', 'IBM'], ['TXN', 'Texas Instruments'],
].map(([symbol, name]) => ({ symbol, name }))
const MACHINE_NODES = [
  { state: 'PUT_CASH_READY', x: 20, y: 35, title: 'Cash ready' },
  { state: 'PUT_OPEN', x: 250, y: 35, title: 'Short put open' },
  { state: 'SHARES_HELD', x: 250, y: 150, title: 'Shares held' },
  { state: 'CALL_OPEN', x: 480, y: 150, title: 'Covered call open' },
  { state: 'CLOSED', x: 480, y: 35, title: 'Cycle closed' },
]
function transitionsFor(state, cycle) {
  const choices = ({
    PUT_OPEN: [
      { target: 'PUT_CASH_READY', action: 'close_option', title: 'Buy put to close', detail: 'Pay the current buyback price. Remaining credit is realized and the cycle returns to cash-ready.' },
      { target: 'PUT_CASH_READY', action: 'expire_otm', title: 'Put expires OTM', detail: 'After expiration, retain the full opening credit and remain cash-ready for another put.' },
      { target: 'SHARES_HELD', action: 'assigned', title: 'Put assignment', detail: 'Record 100 shares per contract at the strike. Economic basis is reduced by the put credit.' },
    ],
    PUT_CASH_READY: [
      { target: 'PUT_OPEN', action: 'sell_put', title: 'Sell another put', detail: 'Open a new short put and record its actual credit, strike, contracts, and expiration.' },
      { target: 'CLOSED', action: 'close_cycle', title: 'Close this cycle', detail: 'Archive the finished cycle. You can still review it in the list.' },
    ],
    SHARES_HELD: [
      { target: 'CALL_OPEN', action: 'sell_call', title: 'Sell covered call', detail: 'Open calls only against full 100-share lots currently recorded.' },
      { target: 'PUT_CASH_READY', action: 'sell_shares', title: 'Sell all shares', detail: 'Record sale proceeds and realize share P&L. A partial sale leaves the cycle in Shares held.' },
    ],
    CALL_OPEN: [
      { target: 'SHARES_HELD', action: 'close_option', title: 'Buy call to close', detail: 'Pay to close the call. Keep the covered shares and realize the option P&L.' },
      { target: 'SHARES_HELD', action: 'expire_otm', title: 'Call expires OTM', detail: 'After expiration, retain the credit and keep the shares.' },
      { target: 'PUT_CASH_READY', action: 'assigned', title: 'All covered shares called away', detail: 'Record the shares sold at the strike. Realized P&L includes share basis and call credit.' },
      { target: 'SHARES_HELD', action: 'assigned', title: 'Some shares called away', detail: 'For a call covering only part of the holding, the remaining shares stay in this cycle.' },
    ],
  }[state] || [])
  if (state === 'CALL_OPEN' && cycle?.activeLeg) {
    const calledShares = cycle.activeLeg.contracts * 100
    const assignmentTarget = calledShares >= cycle.shares ? 'PUT_CASH_READY' : 'SHARES_HELD'
    return choices.filter((item) => item.action !== 'assigned' || item.target === assignmentTarget)
  }
  return choices
}
const MACHINE_ROUTES = [
  ['PUT_CASH_READY', 'PUT_OPEN', 'Sell put', 'M185 62 H244'],
  ['PUT_OPEN', 'PUT_CASH_READY', 'Close / expire', 'M245 86 C220 112 207 112 185 86'],
  ['PUT_OPEN', 'SHARES_HELD', 'Assignment', 'M326 91 V142'],
  ['SHARES_HELD', 'CALL_OPEN', 'Sell call', 'M415 177 H474'],
  ['SHARES_HELD', 'PUT_CASH_READY', 'Sell shares', 'M250 175 C225 148 210 112 185 80'],
  ['CALL_OPEN', 'SHARES_HELD', 'Close / expire', 'M475 198 C450 220 437 220 415 198'],
  ['CALL_OPEN', 'PUT_CASH_READY', 'All shares assigned', 'M512 146 C500 121 462 114 424 93'],
  ['PUT_CASH_READY', 'CLOSED', 'Close cycle', 'M167 38 C255 2 390 2 480 38'],
]

function StateMachine({ state, transitions, chosen, onChoose }) {
  const destinations = new Set(transitions.map((item) => item.target))
  return <section className="panel wheel-panel wheel-machine-panel">
    <div className="wheel-panel-heading"><div><span className="panel-kicker">STATE MACHINE · CLICK A DESTINATION OR TRANSITION</span><h2>Where can this cycle go?</h2></div></div>
    <div className="wheel-machine-scroll"><svg className="wheel-machine-svg" viewBox="0 0 650 235" role="group" aria-label="Wheel cycle state diagram">
      <defs><marker id="wheel-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="currentColor" /></marker></defs>
      {MACHINE_ROUTES.map(([from, to, label, path]) => <g key={`${from}-${to}-${label}`} className={`wheel-route ${state === from && transitions.some((item) => item.target === to) ? 'wheel-route-active' : ''}`}><path d={path} markerEnd="url(#wheel-arrow)" /><text x={path.startsWith('M326') ? 331 : path.startsWith('M512') ? 467 : path.startsWith('M167') ? 322 : path.startsWith('M415') || path.startsWith('M475') ? 445 : 214} y={path.startsWith('M326') ? 120 : path.startsWith('M512') ? 123 : path.startsWith('M167') ? 9 : path.startsWith('M415') || path.startsWith('M475') ? 215 : path.startsWith('M245') ? 115 : 56}>{label}</text></g>)}
      {MACHINE_NODES.map((node) => <g key={node.state} role="button" tabIndex={destinations.has(node.state) ? 0 : -1} aria-label={`${node.title}${state === node.state ? ', current state' : ''}`} onClick={() => destinations.has(node.state) && onChoose(transitions.find((item) => item.target === node.state))} onKeyDown={(event) => { if ((event.key === 'Enter' || event.key === ' ') && destinations.has(node.state)) { event.preventDefault(); onChoose(transitions.find((item) => item.target === node.state)) } }} className={`wheel-machine-node ${state === node.state ? 'is-current' : ''} ${destinations.has(node.state) ? 'is-reachable' : ''} ${chosen?.target === node.state ? 'is-chosen' : ''}`}>
        <rect x={node.x} y={node.y} width="165" height="55" rx="10" /><text x={node.x + 82.5} y={node.y + 24} textAnchor="middle" className="wheel-node-title">{node.title}</text><text x={node.x + 82.5} y={node.y + 41} textAnchor="middle" className="wheel-node-state">{state === node.state ? 'YOU ARE HERE' : destinations.has(node.state) ? 'AVAILABLE NEXT' : node.state.replaceAll('_', ' ')}</text>
      </g>)}
    </svg></div>
    <div className="wheel-machine-mobile"><div className="wheel-mobile-current"><small>CURRENT STATE</small><b>{stateLabels[state]}</b></div><span className="wheel-mobile-down">↓ Available next states</span><div className="wheel-mobile-targets">{[...new Set(transitions.map((item) => item.target))].map((target) => <button key={target} className={`wheel-mobile-target ${chosen?.target === target ? 'is-chosen' : ''}`} onClick={() => onChoose(transitions.find((item) => item.target === target))}><b>{stateLabels[target]}</b><span>Tap to preview transition →</span></button>)}</div></div>
    <div className="wheel-transition-choices">{transitions.map((item) => <button key={item.action + item.title} className={`wheel-transition-choice ${chosen?.title === item.title ? 'is-selected' : ''}`} onClick={() => onChoose(item)}><b>{item.title}</b><span>→ {stateLabels[item.target]}</span></button>)}</div>
    {!transitions.length && <p className="wheel-form-note">This cycle is closed. Delete it from the list if it was only a practice entry.</p>}
  </section>
}

function previewFor(transition, cycle, market) {
  if (!transition || !cycle) return null
  const leg = cycle.activeLeg
  const quantity = leg ? leg.contracts * 100 : 0
  if (transition.action === 'assigned' && leg?.type === 'PUT') return `${quantity} shares would be added at ${money(leg.strike)}. Estimated economic cost basis after the opening credit: ${money(leg.strike - leg.premium)} per share. The broker confirms whether assignment actually occurred.`
  if (transition.action === 'assigned' && leg?.type === 'CALL') return `${quantity} shares would be sold at ${money(leg.strike)}. Estimated realized wheel P&L for this lot: ${money((leg.strike + leg.premium - (cycle.shareCostBasis || 0)) * quantity)}. Shares remaining after assignment: ${Math.max(0, cycle.shares - quantity)}.`
  if (transition.action === 'expire_otm') return `If your broker confirms OTM expiration, this records ${money(leg.premium * quantity)} gross option credit as realized P&L. This action is only allowed on or after the expiration date.`
  if (transition.action === 'close_option') return market?.optionMark == null ? 'Buy-to-close price required. A matching live option quote is unavailable, so review the current quote at your broker before estimating realized P&L. Your actual fill determines the recorded result.' : `Buy-to-close price required. At the current option mark (${money(market.optionMark)}), estimated realized option P&L would be ${money((leg.premium - market.optionMark) * quantity)}. Your actual fill determines the recorded result.`
  if (transition.action === 'sell_put') return 'Choose the next expiration and strike, then enter your actual credit. The app will record the put and return the cycle to Short put open.'
  if (transition.action === 'sell_call') return `Choose a call covered by up to ${Math.floor(cycle.shares / 100)} contract(s), then enter your actual credit. If assigned, the selected shares are sold at the strike.`
  if (transition.action === 'sell_shares') return `Record the number of shares and actual sale price. Selling all ${cycle.shares} shares returns the cycle to Cash ready; selling fewer keeps it in Shares held.`
  if (transition.action === 'close_cycle') return `This archives the cycle with ${money(cycle.realizedPnl)} realized P&L. No shares or open option are currently recorded.`
  return transition.detail
}

async function api(url, options) {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = response.status === 204 ? null : await response.json()
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
  const [backgroundAlerts, setBackgroundAlerts] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [selectedDetails, setSelectedDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [mode, setMode] = useState('put')
  const [symbol, setSymbol] = useState('AAPL')
  const [tickerChoice, setTickerChoice] = useState('AAPL')
  const [customTicker, setCustomTicker] = useState('')
  const [targetTickers, setTargetTickers] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem('wheelTargetTickers') || '[]')
      return [...DEFAULT_TICKERS, ...saved].filter((item, index, all) => all.findIndex((other) => other.symbol === item.symbol) === index)
    } catch { return DEFAULT_TICKERS }
  })
  const [shares, setShares] = useState('100')
  const [basis, setBasis] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [maxLoss, setMaxLoss] = useState('')
  const [expiryDays, setExpiryDays] = useState('7')
  const [newLeg, setNewLeg] = useState({})
  const [actionLeg, setActionLeg] = useState({})
  const [actionForm, setActionForm] = useState('')
  const [selectedTransition, setSelectedTransition] = useState(null)
  const [closePrice, setClosePrice] = useState('')
  const [saleShares, setSaleShares] = useState('')
  const [salePrice, setSalePrice] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function addTargetTicker(value) {
    const ticker = value.trim().toUpperCase()
    if (!/^[A-Z0-9.-]{1,15}$/.test(ticker)) return
    setTargetTickers((current) => {
      if (current.some((item) => item.symbol === ticker)) return current
      const next = [...current, { symbol: ticker, name: 'Custom ticker' }].sort((a, b) => a.symbol.localeCompare(b.symbol))
      try { window.localStorage.setItem('wheelTargetTickers', JSON.stringify(next.filter((item) => !DEFAULT_TICKERS.some((preset) => preset.symbol === item.symbol)))) } catch { /* Local storage can be disabled. */ }
      return next
    })
  }

  const refresh = useCallback(async () => {
    setError('')
    try {
      const items = await api('/api/wheel')
      setCycles(items)
      try { setBackgroundAlerts(await api('/api/wheel/alerts')) } catch { setBackgroundAlerts([]) }
      setSelectedId((current) => current && items.some((item) => item.id === current) ? current : items[0]?.id || '')
    } catch (reason) { setError(reason.message) } finally { setLoading(false) }
  }, [])

  async function dismissBackgroundAlert(alertId) {
    try {
      await api(`/api/wheel/alerts/${alertId}/dismiss`, { method: 'POST' })
      setBackgroundAlerts((items) => items.filter((item) => item.id !== alertId))
    } catch (reason) { setError(reason.message) }
  }

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

  useEffect(() => { setSelectedTransition(null); setActionForm(''); setActionLeg({}) }, [selectedId])

  const selected = useMemo(() => cycles.find((item) => item.id === selectedId) || null, [cycles, selectedId])


  async function submitNew(event) {
    event.preventDefault(); setSubmitting(true); setError('')
    try {
      const payload = { symbol, startMode: mode, takeProfitPercent: takeProfit || null, maxLossDollars: maxLoss || null, expiryAlertDays: expiryDays }
      if (mode === 'put') Object.assign(payload, newLeg)
      else Object.assign(payload, { shares, shareCostBasis: basis })
      const created = await api('/api/wheel', { method: 'POST', body: JSON.stringify(payload) })
      addTargetTicker(symbol)
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

  async function deleteCycle(cycle) {
    if (!window.confirm(`Delete the ${cycle.symbol} wheel instance and all its recorded trade history? This cannot be undone.`)) return
    setSubmitting(true); setError('')
    try { await api(`/api/wheel/${cycle.id}`, { method: 'DELETE' }); await refresh() }
    catch (reason) { setError(reason.message) } finally { setSubmitting(false) }
  }

  function prepareTransition(transition) {
    if (!transition || !selected) return
    if (transition.action === 'close_option') {
      setActionForm('close')
      document.getElementById('wheel-action-controls')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (transition.action === 'sell_put') {
      document.getElementById('wheel-put-controls')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (transition.action === 'sell_call') {
      document.getElementById('wheel-share-controls')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (transition.action === 'sell_shares') {
      document.getElementById('wheel-sell-shares-controls')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else if (transition.action === 'assigned') {
      if (window.confirm(`Record broker-confirmed assignment and move to ${stateLabels[transition.target]}?`)) doAction('assigned')
    } else if (transition.action === 'expire_otm') {
      if (window.confirm('Record that your broker confirmed this option expired out of the money?')) doAction('expire_otm')
    } else if (transition.action === 'close_cycle') {
      if (window.confirm('Close and archive this cash-ready wheel cycle?')) doAction('close_cycle')
    }
  }

  async function openLeg(action, values) {
    const payload = { strike: values.strike, expiration: values.expiration, contracts: values.contracts, premium: values.premium }
    await doAction(action, payload)
  }

  const selectedAnalysis = selected ? analysis[selected.id] : null
  const availableTransitions = selected ? transitionsFor(selected.state, selected) : []
  const chosenTransition = availableTransitions.find((item) => item.title === selectedTransition?.title) || null
  const showOptionTransitionPreview = ['sell_put', 'sell_call'].includes(chosenTransition?.action) && Boolean(actionLeg.strike) && actionLeg.premium !== ''

  return <div className="wheel-page">
    <section className="analysis-heading wheel-heading">
      <div><div className="eyebrow">OPTIONS WORKSPACE <span>·</span> TRACK EVERY LEG</div><h1>Wheel strategy</h1><p>Track cash-secured puts, assignment, covered calls, closes, and the next cycle.</p></div>
      <button className="wheel-primary-button" onClick={() => { setMode('put'); setTickerChoice('AAPL'); setSymbol('AAPL'); setShowNew((open) => !open) }}>{showNew ? 'Cancel new cycle' : '+ New wheel cycle'}</button>
    </section>

    <div className="wheel-disclaimer"><b>Research tracker, not trade execution.</b> Quote data can be delayed or incomplete. Assignment is determined by your broker; confirm the actual outcome before recording it. Alerts apply only to the thresholds you set.</div>
    {backgroundAlerts.length > 0 && <section className="panel wheel-panel wheel-background-alerts"><div className="wheel-panel-heading"><div><span className="panel-kicker">SCHEDULED MARKET CHECKS</span><h2>Review alerts <span className="wheel-alert-count">{backgroundAlerts.length}</span></h2></div><small>Checks run every 15 minutes during US market hours.</small></div><div className="wheel-background-alert-list">{backgroundAlerts.map((alert) => <div key={alert.id} className={`wheel-background-alert wheel-background-${alert.level}`}><button className="wheel-background-alert-main" onClick={() => setSelectedId(alert.cycleId)}><b>{alert.symbol}</b><span>{alert.message}</span><small>Last checked {new Date(alert.lastSeen).toLocaleString()}</small></button><button className="wheel-quiet-button" onClick={() => dismissBackgroundAlert(alert.id)}>Dismiss</button></div>)}</div><div className="wheel-form-note">These alerts flag your saved thresholds for review. They do not select a trade or place an order.</div></section>}
    {error && <div className="wheel-error">{error}</div>}

    {showNew && <section className="panel wheel-panel new-wheel-panel">
      <div className="wheel-panel-heading"><div><span className="panel-kicker">CREATE A TRACKED INSTANCE</span><h2>Start a wheel cycle</h2></div></div>
      <form className="wheel-form" onSubmit={submitNew}>
        <div className="wheel-form-grid">
          <label>TARGET TICKER<select value={tickerChoice} onChange={(event) => { const value = event.target.value; setTickerChoice(value); if (value !== 'CUSTOM') setSymbol(value) }}><optgroup label="Target tickers">{targetTickers.map((item) => <option key={item.symbol} value={item.symbol}>{item.symbol} · {item.name}</option>)}</optgroup><option value="CUSTOM">Enter a new ticker…</option></select></label>
          <label>STARTING POINT<select value={mode} onChange={(event) => setMode(event.target.value)}><option value="put">Sell a cash-secured put</option><option value="shares">I already own shares</option></select></label>
        </div>
        {tickerChoice === 'CUSTOM' && <div className="wheel-custom-ticker"><label>NEW TICKER<input value={customTicker} onChange={(event) => { const value = event.target.value.toUpperCase(); setCustomTicker(value); setSymbol(value) }} placeholder="e.g. COST" maxLength="15" /></label><button type="button" className="wheel-quiet-button" disabled={!/^[A-Z0-9.-]{1,15}$/.test(customTicker)} onClick={() => { addTargetTicker(customTicker); setTickerChoice(customTicker); setSymbol(customTicker); setCustomTicker('') }}>Add to target list</button></div>}
        {mode === 'put' ? <ContractPicker key={`${symbol}-PUT-new`} symbol={symbol} type="PUT" onValues={setNewLeg} /> : <div className="wheel-form-grid"><label>SHARES OWNED<input type="number" min="1" step="1" value={shares} onChange={(event) => setShares(event.target.value)} /></label><label>AVERAGE COST / SHARE<input type="number" min="0.01" step="0.01" value={basis} onChange={(event) => setBasis(event.target.value)} placeholder="Your recorded cost" /></label></div>}
        <div className="wheel-form-grid wheel-alert-inputs">
          <label>PROFIT-CAPTURE ALERT % <input type="number" min="1" max="99.9" step="0.1" value={takeProfit} onChange={(event) => setTakeProfit(event.target.value)} placeholder="Optional" /></label>
          <label>LOSS ALERT $ <input type="number" min="0.01" step="0.01" value={maxLoss} onChange={(event) => setMaxLoss(event.target.value)} placeholder="Optional" /></label>
          <label>EXPIRY ALERT · DAYS <input type="number" min="0" step="1" value={expiryDays} onChange={(event) => setExpiryDays(event.target.value)} /></label>
        </div>
        <div className="wheel-form-note">Optional alerts are user-set thresholds; blank thresholds are not guessed for you. Option bid/ask is context only—enter your actual premium fill.</div>
        <button className="wheel-primary-button" disabled={submitting || !/^[A-Z0-9.-]{1,15}$/.test(symbol) || (mode === 'put' && (!newLeg.strike || !newLeg.premium || !newLeg.expiration)) || (mode === 'shares' && (!shares || !basis))}>{submitting ? 'Saving…' : 'Create cycle'}</button>
      </form>
    </section>}

    <div className="wheel-layout">
      <section className="wheel-cycle-list">
        <div className="wheel-list-heading"><div><span className="panel-kicker">YOUR TRACKED POSITIONS</span><h2>Wheel instances</h2></div><button className="wheel-quiet-button" onClick={refresh}>Refresh</button></div>
        {loading ? <div className="table-loading"><span className="loader" />Loading tracked cycles…</div> : cycles.length === 0 ? <div className="panel wheel-empty">No wheel cycles yet. Start with a put or record shares you already own.</div> : cycles.map((item) => <div key={item.id} className={`wheel-cycle-card ${selectedId === item.id ? 'wheel-cycle-selected' : ''}`}>
          <button className="wheel-cycle-select" onClick={() => setSelectedId(item.id)} aria-pressed={selectedId === item.id}>
            <span className="wheel-cycle-top"><b>{item.symbol}</b><i>{stateLabels[item.state] || item.state}</i></span>
            <span className="wheel-cycle-sub">{item.activeLeg ? `${item.activeLeg.type} ${money(item.activeLeg.strike)} · ${prettyDate(item.activeLeg.expiration)}` : `${item.shares} shares · ${money(item.shareCostBasis)} basis`}</span>
            <span className={`wheel-pnl ${item.realizedPnl >= 0 ? 'wheel-positive' : 'wheel-negative'}`}>Realized {money(item.realizedPnl)}</span>
          </button><button className="wheel-delete-button" onClick={() => deleteCycle(item)} disabled={submitting} aria-label={`Delete ${item.symbol} wheel instance`}>Delete</button>
        </div>)}
      </section>

      <section className="wheel-detail-column">
        {!selected ? <div className="panel wheel-empty">Choose a wheel cycle to see its current state and history.</div> : <>
          <StateMachine state={selected.state} transitions={availableTransitions} chosen={chosenTransition} onChoose={setSelectedTransition} />
          {chosenTransition && <section className="panel wheel-panel wheel-transition-preview">
            <div className="wheel-panel-heading"><div><span className="panel-kicker">TRANSITION PREVIEW · {selected.state.replaceAll('_', ' ')}</span><h2>{chosenTransition.title}</h2></div><span className="wheel-state-arrow">→ {stateLabels[chosenTransition.target]}</span></div>
            <p>{previewFor(chosenTransition, selected, selectedAnalysis)}</p>
            <div className="wheel-preview-metrics"><span>Realized P&amp;L now <b>{money(selected.realizedPnl)}</b></span>{selected.activeLeg && <><span>Option credit <b>{money(selected.activeLeg.premium)} / share</b></span><span>Contracts <b>{selected.activeLeg.contracts}</b></span></>}{selected.shares > 0 && <span>Shares at risk <b>{selected.shares}</b></span>}{selectedAnalysis?.underlyingPrice != null && <span>Current underlying <b>{money(selectedAnalysis.underlyingPrice)}</b></span>}</div>
            {showOptionTransitionPreview && (
              <div className="wheel-preview-metrics">
                <span>Proposed strike <b>{money(actionLeg.strike)}</b></span>
                <span>Gross credit at entered fill <b>{money(Number(actionLeg.premium) * Number(actionLeg.contracts) * 100)}</b></span>
                {chosenTransition.action === 'sell_put' ? <span>Put break-even at expiry <b>{money(Number(actionLeg.strike) - Number(actionLeg.premium))}</b></span> : null}
                <span>Expiration <b>{prettyDate(actionLeg.expiration)}</b></span>
                <small className="wheel-form-note">Gross estimate before fees; not an order quote.</small>
              </div>
            )}
            {chosenTransition.action === 'sell_shares' && saleShares && salePrice && <div className="wheel-preview-metrics"><span>Estimated share P&amp;L <b>{money((Number(salePrice) - Number(selected.shareCostBasis || 0)) * Number(saleShares))}</b></span><span>Shares remaining <b>{Math.max(0, selected.shares - Number(saleShares))}</b></span></div>}
            <button className="wheel-primary-button" disabled={submitting} onClick={() => prepareTransition(chosenTransition)}>{chosenTransition.action === 'assigned' || chosenTransition.action === 'expire_otm' || chosenTransition.action === 'close_cycle' ? 'Review and record transition' : chosenTransition.action === 'close_option' ? 'Enter close price' : 'Open transition inputs'}</button>
          </section>}
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
                {selectedAnalysis?.reviewGuidance && <div className="wheel-review-guidance"><b>{selectedAnalysis.reviewGuidance.status}</b><span>{selectedAnalysis.reviewGuidance.message}</span><small>Rule-based review context, not an instruction to trade.</small></div>}
                {selectedAnalysis?.underlyingPrice != null && <div className="wheel-market-metrics"><span>Underlying <b>{money(selectedAnalysis.underlyingPrice)}</b></span><span>Option mark <b>{money(selectedAnalysis.optionMark)}</b></span><span>Open P&amp;L <b className={(selectedAnalysis.unrealizedPnl || 0) >= 0 ? 'wheel-positive' : 'wheel-negative'}>{money(selectedAnalysis.unrealizedPnl)}</b></span><span>Captured <b>{selectedAnalysis.premiumCapturedPercent == null ? '—' : `${selectedAnalysis.premiumCapturedPercent.toFixed(0)}%`}</b></span><span>Break-even at expiry <b>{money(selectedAnalysis.breakEvenAtExpiration)}</b></span>{selectedAnalysis.coveredCallAssignmentPnl != null && <span>If assigned <b className={selectedAnalysis.coveredCallAssignmentPnl >= 0 ? 'wheel-positive' : 'wheel-negative'}>{money(selectedAnalysis.coveredCallAssignmentPnl)}</b></span>}<span>Days left <b>{selectedAnalysis.daysToExpiration}</b></span></div>}
                <p>{selectedAnalysis?.nextScenarios || (selected.activeLeg.type === 'PUT' ? 'If OTM at expiry: cash-ready for another put. If assigned: shares-held, then covered calls.' : 'If OTM at expiry: keep shares and consider the next call. If assigned: shares are called away and the cycle returns to puts.')}</p>
                {selectedAnalysis?.alerts?.length > 0 && <div className="wheel-alert-list">{selectedAnalysis.alerts.map((alert, index) => <div key={`${alert.code || alert.message}-${index}`} className={`wheel-alert wheel-alert-${alert.level}`}><span>{alert.level === 'risk' ? '!' : alert.level === 'action' ? '●' : '·'}</span>{alert.message}</div>)}</div>}
                <small className="wheel-data-note">{selectedAnalysis?.dataSource || 'Underlying and option quotes may be delayed, incomplete, or unavailable. No orders are placed.'}</small>
              </div>
              <div className="wheel-actions" id="wheel-action-controls">
                {actionForm === 'close' ? <div className="wheel-inline-form"><label>BUY-TO-CLOSE PRICE / SHARE<input type="number" min="0" step="0.01" value={closePrice} onChange={(event) => setClosePrice(event.target.value)} /></label><button className="wheel-primary-button" disabled={submitting || closePrice === ''} onClick={() => doAction('close_option', { closePrice })}>Record close</button><button className="wheel-quiet-button" onClick={() => setActionForm('')}>Cancel</button></div> : <button className="wheel-secondary-button" onClick={() => setActionForm('close')}>Record buy-to-close</button>}
                <button className="wheel-secondary-button" disabled={submitting} onClick={() => doAction('expire_otm')}>Record expired OTM</button>
                <button className="wheel-secondary-button" disabled={submitting} onClick={() => doAction('assigned')}>Record assignment</button>
              </div>
            </> : <div className="wheel-position-grid wheel-holding-grid"><div><small>SHARES HELD</small><b>{selected.shares}</b></div><div><small>ECONOMIC BASIS / SHARE</small><b>{money(selected.shareCostBasis)}</b></div><div><small>REALIZED P&amp;L</small><b>{money(selected.realizedPnl)}</b></div><div><small>STATE</small><b>{selected.state === 'PUT_CASH_READY' ? 'No shares or open option' : 'Shares recorded'}</b></div></div>}
          </section>

          {selected.state === 'PUT_CASH_READY' && <section className="panel wheel-panel" id="wheel-put-controls"><div className="wheel-panel-heading"><div><span className="panel-kicker">NEXT LOOP</span><h2>Sell another put</h2></div></div><ContractPicker key={`${selected.id}-PUT-${selected.updatedAt}`} symbol={selected.symbol} type="PUT" compact onValues={setActionLeg} /><div className="wheel-form-actions"><button className="wheel-primary-button" disabled={submitting || !actionLeg.strike || !actionLeg.premium || !actionLeg.expiration} onClick={() => openLeg('sell_put', actionLeg)}>Record put sale</button><button className="wheel-quiet-button" disabled={submitting} onClick={() => doAction('close_cycle')}>Close cycle</button></div></section>}
          {selected.state === 'SHARES_HELD' && <>
            <section className="panel wheel-panel" id="wheel-share-controls"><div className="wheel-panel-heading"><div><span className="panel-kicker">COVERED-CALL STAGE</span><h2>Sell a covered call</h2></div><span className="wheel-call-cover">{Math.floor(selected.shares / 100)} contracts covered</span></div><ContractPicker key={`${selected.id}-CALL-${selected.updatedAt}`} symbol={selected.symbol} type="CALL" compact onValues={setActionLeg} /><div className="wheel-form-actions"><button className="wheel-primary-button" disabled={submitting || !actionLeg.strike || !actionLeg.premium || !actionLeg.expiration || Number(actionLeg.contracts) * 100 > selected.shares} onClick={() => openLeg('sell_call', actionLeg)}>Record call sale</button></div></section>
            <section className="panel wheel-panel" id="wheel-sell-shares-controls"><div className="wheel-panel-heading"><div><span className="panel-kicker">OPTIONAL MANUAL CLOSE</span><h2>Sell shares</h2></div></div><div className="wheel-inline-form"><label>SHARES TO SELL<input type="number" min="1" max={selected.shares} step="1" value={saleShares} onChange={(event) => setSaleShares(event.target.value)} /></label><label>SALE PRICE / SHARE<input type="number" min="0" step="0.01" value={salePrice} onChange={(event) => setSalePrice(event.target.value)} /></label><button className="wheel-secondary-button" disabled={submitting || !saleShares || !salePrice} onClick={() => doAction('sell_shares', { shares: saleShares, price: salePrice })}>Record share sale</button></div></section>
          </>}

          <section className="panel wheel-panel wheel-history-panel"><div className="wheel-panel-heading"><div><span className="panel-kicker">AUDIT TRAIL</span><h2>State transitions</h2></div></div>{selectedDetails?.events?.length ? <div className="wheel-event-list">{selectedDetails.events.map((event) => <div key={event.id} className="wheel-event"><span className="wheel-event-dot" /><div><b>{event.type.replaceAll('_', ' ')}</b><small>{event.fromState?.replaceAll('_', ' ') || 'Start'} → {event.toState.replaceAll('_', ' ')}</small></div><time>{new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(event.createdAt))}</time></div>)}</div> : <div className="wheel-form-note">No recorded transitions yet.</div>}</section>
        </>}
      </section>
    </div>
    <div className="wheel-footer-note">Strategy results depend on the underlying price, option liquidity, early exercise, contract assignment, taxes, commissions, and corporate actions. The tracker records your actions; it does not connect to a brokerage or tell you which trade to place.</div>
  </div>
}

export default WheelStrategy
