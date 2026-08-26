import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

const API_ROOT = 'https://api.github.com'

function parseRepositoryUrl(value) {
  const parsed = new URL(value.trim())
  if (parsed.hostname !== 'github.com') throw new Error('Enter a valid github.com repository URL.')
  const parts = parsed.pathname.split('/').filter(Boolean)
  if (parts.length < 2) throw new Error('That URL needs both an owner and a repository name.')
  return { owner: parts[0], name: parts[1].replace(/\.git$/, '') }
}

async function fetchFiles(repository, path = '') {
  const response = await fetch(`${API_ROOT}/repos/${repository.owner}/${repository.name}/contents/${path}`)
  if (!response.ok) {
    if (response.status === 404) throw new Error('Repository not found, or it is private.')
    if (response.status === 403) throw new Error('GitHub rate limit reached. Try again later or add authentication.')
    throw new Error(`GitHub returned an error (${response.status}).`)
  }
  const entries = await response.json()
  if (!Array.isArray(entries)) throw new Error('This repository path is not a directory.')
  const nested = await Promise.all(entries.map((entry) => (
    entry.type === 'dir' ? fetchFiles(repository, entry.path) : Promise.resolve([entry.path])
  )))
  return nested.flat()
}

function FileIcon() {
  return <span className="file-icon" aria-hidden="true">•</span>
}

function buildFileTree(files) {
  const root = { directories: {}, files: [] }
  files.forEach((file) => {
    const parts = file.split('/')
    const fileName = parts.pop()
    let current = root
    parts.forEach((part) => {
      current.directories[part] ??= { directories: {}, files: [] }
      current = current.directories[part]
    })
    current.files.push(fileName)
  })
  return root
}

function FileTree({ node, depth = 0 }) {
  const directories = Object.entries(node.directories).sort(([a], [b]) => a.localeCompare(b))
  const files = [...node.files].sort((a, b) => a.localeCompare(b))
  return (
    <div className="tree-level">
      {directories.map(([name, child]) => (
        <div className="tree-directory" key={name}>
          <div className="tree-row folder-row" style={{ '--depth': depth }}>
            <span className="folder-chevron" aria-hidden="true">⌄</span>
            <span className="folder-icon" aria-hidden="true" />
            <span>{name}</span>
          </div>
          <FileTree node={child} depth={depth + 1} />
        </div>
      ))}
      {files.map((file) => (
        <div className="tree-row file-row" style={{ '--depth': depth }} key={file}>
          <FileIcon /><span>{file}</span>
        </div>
      ))}
    </div>
  )
}

function App() {
  const [url, setUrl] = useState('')
  const [files, setFiles] = useState([])
  const [repository, setRepository] = useState(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setStatus('loading')
    try {
      const parsed = parseRepositoryUrl(url)
      const foundFiles = await fetchFiles(parsed)
      setRepository(parsed)
      setFiles(foundFiles)
      setStatus('success')
    } catch (requestError) {
      setError(requestError instanceof TypeError ? 'Enter a complete GitHub URL, including https://' : requestError.message)
      setStatus('error')
    }
  }

  function reset() {
    setUrl('')
    setFiles([])
    setRepository(null)
    setError('')
    setStatus('idle')
  }

  return (
    <main className={status === 'success' ? 'app results-mode' : 'app'}>
      <header className="topbar">
        <button className="brand" onClick={reset} type="button" aria-label="Start a new scan">
          <span className="brand-mark">/</span> repo<span className="brand-dot">.</span>map
        </button>
        <span className="status-pill"><span className="status-dot" /> GitHub explorer</span>
      </header>
      <section className="workspace">
        <div className="intro">
          <p className="eyebrow">Repository intelligence <span>01</span></p>
          <h1>See the shape<br />of any repo<span>.</span></h1>
          <p className="lede">Paste a public GitHub URL and get a clean, navigable view of every file inside.</p>
        </div>
        <form className="url-form" onSubmit={handleSubmit}>
          <label htmlFor="repo-url">GitHub repository URL</label>
          <div className={`input-wrap ${status === 'error' ? 'has-error' : ''}`}>
            <span className="input-prefix">github.com /</span>
            <input id="repo-url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="owner / repository" autoComplete="url" required />
            <button type="submit" disabled={status === 'loading'} aria-label="Scan repository">
              {status === 'loading' ? <span className="spinner" /> : <span>↗</span>}
            </button>
          </div>
          {error && <p className="error-message">{error}</p>}
          <p className="form-hint">Press <kbd>Enter</kbd> to scan <span>·</span> Public repositories only</p>
        </form>
        {status === 'success' && (
          <section className="file-panel" aria-live="polite">
            <div className="panel-heading">
              <div><p className="eyebrow">Scan complete</p><h2>{repository.owner} / {repository.name}</h2></div>
              <div className="file-count"><strong>{files.length}</strong><span>files found</span></div>
            </div>
            {files.length ? <div className="file-list"><div className="tree-root"><div className="tree-row root-row"><span className="folder-icon" aria-hidden="true" /><strong>{repository.name}</strong></div><FileTree node={buildFileTree(files)} /></div></div> : <p className="empty-state">No files found in this repository.</p>}
          </section>
        )}
      </section>
      <footer><span>Built for curious minds</span><span>Public GitHub API <i /></span></footer>
    </main>
  )
}

createRoot(document.querySelector('#app')).render(<App />)
