import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'

type Entry = { id: number; at: string; actor: string; action: string; target: string; detail: Record<string, unknown>; ip: string }

export function Component() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [more, setMore] = useState(true)
  const [error, setError] = useState('')

  const load = (before?: number) =>
    api<Entry[]>(`/admin/audit?limit=100${before ? `&before=${before}` : ''}`)
      .then((rows) => { setEntries((prev) => (before ? [...prev, ...rows] : rows)); setMore(rows.length === 100) })
      .catch((e) => setError(e.message))

  useEffect(() => { void load() }, [])

  return (
    <div className="container-page space-y-8">
      <div>
        <p className="eyebrow mb-2">Admin</p>
        <h1 className="text-2xl font-semibold tracking-tight">Audit log</h1>
        <p className="mt-2 text-sm text-muted">Every admin action, sync, and sign-in event, newest first. Entries cannot be edited or deleted from the website.</p>
      </div>
      {error && <p className="text-sm text-warn">{error}</p>}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="border-b border-line text-left text-xs text-muted">
            <tr><th className="px-4 py-3 font-medium">When (UTC)</th><th className="px-4 py-3 font-medium">Action</th><th className="px-4 py-3 font-medium">Actor</th><th className="px-4 py-3 font-medium">Target</th><th className="px-4 py-3 font-medium">Detail</th><th className="px-4 py-3 font-medium">IP</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {entries.map((e) => (
              <tr key={e.id} className="align-top">
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs">{fmtDate(e.at + 'Z', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' })}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{e.action}</td>
                <td className="px-4 py-2.5 text-xs">{e.actor || <span className="text-muted">system</span>}</td>
                <td className="px-4 py-2.5 text-xs">{e.target}</td>
                <td className="max-w-xs break-words px-4 py-2.5 font-mono text-[11px] text-muted">{Object.keys(e.detail ?? {}).length ? JSON.stringify(e.detail) : ''}</td>
                <td className="px-4 py-2.5 font-mono text-xs text-muted">{e.ip}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {more && entries.length > 0 && <button className="btn-ghost" onClick={() => void load(entries[entries.length - 1].id)}>Load older</button>}
    </div>
  )
}
