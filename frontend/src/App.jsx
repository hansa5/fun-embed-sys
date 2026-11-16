import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const API = '/api'

function currentDocument() {
  return new URLSearchParams(window.location.search).get('doc') || ''
}

function Icon({ name, size = 18 }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }
  const paths = {
    book: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 5.5v16M8 7h8M8 11h7"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    file: <><path d="M13 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10z"/><path d="M13 3v7h7M8 14h8M8 17h6"/></>,
  }
  return <svg {...common}>{paths[name] || paths.file}</svg>
}

function InternalMarkdownLink({ href, documentPath, navigate, children, ...props }) {
  const internalMarkdown = typeof href === 'string' && !/^[a-z][a-z\d+.-]*:/i.test(href) && href.toLowerCase().split(/[?#]/)[0].endsWith('.md')
  if (!internalMarkdown) return <a href={href} {...props}>{children}</a>

  let target = href
  let fragment = ''
  try {
    const url = new URL(href, `https://docs.local/${documentPath}`)
    target = decodeURIComponent(url.pathname.replace(/^\//, ''))
    fragment = url.hash
  } catch {
    return <a href={href} {...props}>{children}</a>
  }
  return <a href={`?doc=${encodeURIComponent(target)}${fragment}`} onClick={(event) => { event.preventDefault(); navigate(target, fragment) }} {...props}>{children}</a>
}

function App() {
  const [documents, setDocuments] = useState([])
  const [activePath, setActivePath] = useState(currentDocument())
  const [document, setDocument] = useState(null)
  const [filter, setFilter] = useState('')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const navigate = useCallback((path, fragment = '') => {
    const query = new URLSearchParams(window.location.search)
    query.set('doc', path)
    window.history.pushState({}, '', `${window.location.pathname}?${query.toString()}${fragment}`)
    setActivePath(path)
    setMobileNavOpen(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

  useEffect(() => {
    const onPopState = () => setActivePath(currentDocument())
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  useEffect(() => {
    let cancelled = false
    fetch(`${API}/documents`).then((response) => {
      if (!response.ok) throw new Error('Could not load the document list.')
      return response.json()
    }).then((items) => {
      if (cancelled) return
      setDocuments(items)
      const queryDoc = currentDocument()
      const initial = items.some((item) => item.path === queryDoc) ? queryDoc : (items[0]?.path || '')
      if (!queryDoc && initial) {
        const query = new URLSearchParams(window.location.search)
        query.set('doc', initial)
        window.history.replaceState({}, '', `${window.location.pathname}?${query.toString()}`)
      }
      setActivePath(initial)
      setLoading(false)
    }).catch((reason) => {
      if (!cancelled) { setError(reason.message); setLoading(false) }
    })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!activePath) return undefined
    let cancelled = false
    setDocument(null)
    fetch(`${API}/documents/${activePath.split('/').map(encodeURIComponent).join('/')}`).then((response) => {
      if (!response.ok) throw new Error('This Markdown document could not be found.')
      return response.json()
    }).then((result) => { if (!cancelled) { setDocument(result); setError('') } })
      .catch((reason) => { if (!cancelled) setError(reason.message) })
    return () => { cancelled = true }
  }, [activePath])

  const filtered = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase()
    return documents.filter((item) => !query || `${item.path} ${item.title}`.toLocaleLowerCase().includes(query))
  }, [documents, filter])
  const groups = useMemo(() => {
    const result = []
    for (const item of filtered) {
      const section = item.path.includes('/') ? item.path.split('/')[0].replaceAll('-', ' ') : 'Overview'
      let group = result[result.length - 1]
      if (!group || group.section !== section) {
        group = { section, items: [] }
        result.push(group)
      }
      group.items.push(item)
    }
    return result
  }, [filtered])

  function chooseDocument(path) {
    navigate(path)
  }

  return (
    <div className="app-shell">
      {mobileNavOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <a className="brand" href="/" onClick={(event) => { event.preventDefault(); if (documents[0]) chooseDocument(documents[0].path) }}>
          <span className="brand-mark"><Icon name="book" size={20} /></span>
          <span className="brand-copy"><strong>Fieldnotes</strong><small>EMBEDDED SYSTEMS</small></span>
        </a>
        <div className="sidebar-caption">PROJECT LIBRARY <span>{String(documents.length).padStart(2, '0')}</span></div>
        <label className="search-box">
          <Icon name="search" size={17} />
          <input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Find a guide…" aria-label="Filter guides" />
          <kbd>/</kbd>
        </label>
        <nav className="document-list" aria-label="Documentation">
          {groups.map((group) => <div className="nav-entry" key={group.section}>
            <span className="nav-section">{group.section}</span>
            {group.items.map((item) => <button className={`nav-link ${activePath === item.path ? 'nav-link-active' : ''}`} key={item.path} onClick={() => chooseDocument(item.path)}>
                <Icon name="file" size={16} /><span>{item.title}</span>
            </button>)}
          </div>)}
          {!loading && filtered.length === 0 && <p className="empty-list">No guides match that search.</p>}
        </nav>
        <div className="sidebar-bottom"><span className="status-dot" /> <span>Local knowledge base</span><span className="version-label">v1.0</span></div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <button className="mobile-menu icon-button" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Icon name="menu" /></button>
          <div className="topbar-path"><span>LIBRARY</span><b>/</b><span className="path-current">{document?.path || 'DOCUMENTATION'}</span></div>
          <div className="topbar-right"><span className="connection-pill"><i /> LIBRARY READY</span></div>
        </header>

        <section className="content-wrap">
          {loading && <div className="loading-state"><span className="loader" />Loading your library</div>}
          {error && <div className="error-card"><strong>Couldn’t load this page</strong><p>{error}</p><button onClick={() => window.location.reload()}>Try again</button></div>}
          {!loading && !error && document && <>
            <div className="article-meta"><span className="meta-chip">FIELD GUIDE</span><span className="meta-divider">·</span><span>docs/{document.path}</span></div>
            <article className="markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
                a: ({ href, children, ...props }) => <InternalMarkdownLink href={href} documentPath={document.path} navigate={navigate} {...props}>{children}</InternalMarkdownLink>,
                table: ({ children }) => <div className="table-scroll"><table>{children}</table></div>,
                img: ({ alt, ...props }) => <img alt={alt || ''} loading="lazy" {...props} />,
              }}>{document.content}</ReactMarkdown>
            </article>
            <footer className="article-footer"><span>END OF GUIDE</span><span>MADE FOR THE WORKBENCH <b>✳</b></span></footer>
          </>}
          {!loading && !error && documents.length === 0 && <div className="error-card"><strong>No Markdown files found</strong><p>Add guides under the docs directory.</p></div>}
        </section>
      </main>
    </div>
  )
}

export default App
