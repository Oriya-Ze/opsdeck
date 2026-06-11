import { useCallback, useEffect, useRef, useState } from 'react'
import { FitAddon } from '@xterm/addon-fit'
import { Terminal } from '@xterm/xterm'
import '@xterm/xterm/css/xterm.css'
import { Plug, Terminal as TerminalIcon, Unplug } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../hooks/useFetch'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PageHeader } from '../components/PageHeader'
import type { TerminalTargetOption } from '../types'

function buildWsUrl(target: TerminalTargetOption, cols: number, rows: number) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const params = new URLSearchParams({
    target: target.target,
    cols: String(cols),
    rows: String(rows),
  })
  if (target.node_id) params.set('node_id', target.node_id)
  return `${proto}//${window.location.host}/api/terminal/ws?${params}`
}

export function TerminalPage() {
  const { data: options, loading } = useFetch(() => api.getTerminalOptions())
  const [selectedId, setSelectedId] = useState('controller')
  const [connected, setConnected] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<Terminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  const selected = options?.targets.find((t) => t.id === selectedId) ?? options?.targets[0]

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    termRef.current?.dispose()
    termRef.current = null
    fitRef.current = null
    setConnected(false)
    setStatus(null)
  }, [])

  const sendResize = useCallback(() => {
    const term = termRef.current
    const ws = wsRef.current
    if (!term || !ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(
      JSON.stringify({
        type: 'resize',
        cols: term.cols,
        rows: term.rows,
      }),
    )
  }, [])

  const connect = useCallback(() => {
    if (!selected || !containerRef.current) return

    disconnect()
    setError(null)

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      theme: {
        background: '#111827',
        foreground: '#e5e7eb',
        cursor: '#38bdf8',
      },
      convertEol: true,
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(containerRef.current)
    fit.fit()

    termRef.current = term
    fitRef.current = fit

    const ws = new WebSocket(buildWsUrl(selected, term.cols, term.rows))
    wsRef.current = ws
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => {
      setConnected(true)
      setStatus(`Connected to ${selected.label}`)
      sendResize()
      term.focus()
    }

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        term.write(event.data)
      } else {
        term.write(new Uint8Array(event.data as ArrayBuffer))
      }
    }

    ws.onerror = () => {
      setError('Terminal connection failed')
      disconnect()
    }

    ws.onclose = (event) => {
      if (event.reason) {
        setError(event.reason)
      }
      setConnected(false)
      setStatus(null)
    }

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })
  }, [disconnect, selected, sendResize])

  useEffect(() => {
    const onResize = () => {
      fitRef.current?.fit()
      sendResize()
    }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      disconnect()
    }
  }, [disconnect, sendResize])

  if (loading) return <LoadingSpinner />

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <PageHeader
        title="Terminal"
        description="Interactive shell on the Ansible controller or a managed node via SSH"
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <select
          className="select sm:max-w-xs"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          disabled={connected}
        >
          {options?.targets.map((target) => (
            <option key={target.id} value={target.id}>
              {target.label}
            </option>
          ))}
        </select>

        {selected && (
          <span className="text-sm text-gray-500 self-center">{selected.description}</span>
        )}

        <div className="flex gap-2 sm:ml-auto">
          {!connected ? (
            <button className="btn-primary flex items-center gap-2" onClick={connect} disabled={!selected}>
              <Plug size={14} /> Connect
            </button>
          ) : (
            <button className="btn-secondary flex items-center gap-2" onClick={disconnect}>
              <Unplug size={14} /> Disconnect
            </button>
          )}
        </div>
      </div>

      {status && <p className="text-sm text-emerald-400 mb-2">{status}</p>}
      {error && <p className="text-sm text-red-400 mb-2">{error}</p>}

      <div className="card flex-1 p-0 overflow-hidden min-h-[420px] flex flex-col">
        {!connected && (
          <div className="flex items-center justify-center gap-2 text-gray-500 flex-1">
            <TerminalIcon size={18} />
            Select a target and click Connect
          </div>
        )}
        <div
          ref={containerRef}
          className={`flex-1 p-2 ${connected ? 'block' : 'hidden'}`}
          style={{ minHeight: 400 }}
        />
      </div>
    </div>
  )
}
