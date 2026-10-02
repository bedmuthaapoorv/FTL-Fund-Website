import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { FormError } from '../components/AuthCard'
import { api } from '../lib/api'
import { fmtDate } from '../lib/format'

type Run = { id: number; received_at: string; generated_at: string | null; status: 'applied' | 'rejected'; nav_points: number; investors: number; events: number; payload_sha256: string; message: string }
type Status = { as_of: string | null; current_generation: number; runs: Run[] }

const dt = (iso: string) => fmtDate(iso + 'Z', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })

export function Component() {
  const [status, setStatus] = useState<Status | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = useCallback(() => api<Status>('/admin/sync-runs').then(setStatus).catch((e) => setError(e.message)), [])
  useEffect(() => { void load() }, [load])

  const onFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError('')
    setNotice('')
    try {
      const res = await fetch('/api/admin/sync/upload', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-FTH-CSRF': '1' },
        body: await file.text(),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Upload rejected.')
      setNotice(`Applied: ${data.nav_points} NAV points, ${data.investors} investors, ${data.events} capital events.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.')
    }
    void load()
  }

  return (
    <div className="container-page space-y-10">
      <div>
        <p className="eyebrow mb-2">Admin</p>
        <h1 className="text-2xl font-semibold tracking-tight">Data sync</h1>
        <p className="mt-2 max-w-prose text-sm text-muted">
          FrontierTradeLight stays the source of truth. A script on your machine reads the Fund Manager files, replaces
          investor IDs with pseudonyms, and pushes a signed snapshot here. Each sync replaces all fund data. This website
          never connects to your machine.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="card p-5"><p className="text-xs text-muted">Data as of</p><p className="mt-2 font-mono text-lg">{status?.as_of ? dt(status.as_of) : 'Never synced'}</p></div>
        <div className="card p-5"><p className="text-xs text-muted">Current generation</p><p className="mt-2 font-mono text-lg">{status?.current_generation ?? '—'}</p></div>
        <div className="card p-5">
          <p className="text-xs text-muted">Manual upload</p>
          <label className="btn-ghost mt-2 cursor-pointer !py-1.5">
            Upload snapshot.json
            <input type="file" accept="application/json,.json" className="sr-only" onChange={onFile} />
          </label>
        </div>
      </section>

      {notice && <p role="status" className="rounded-md bg-accent-soft px-3 py-2 text-sm">{notice}</p>}
      <FormError>{error}</FormError>

      <section className="card p-5 sm:p-6">
        <h2 className="text-base font-semibold">Run a sync from your machine</h2>
        <pre className="mt-3 overflow-x-auto rounded-md bg-ground p-4 font-mono text-xs leading-relaxed text-ink">{`cd sync
python3 export_snapshot.py            # dry run: validates and writes out/snapshot.json
python3 export_snapshot.py --push     # signs and sends it here`}</pre>
      </section>

      <section>
        <h2 className="mb-4 text-base font-semibold">History</h2>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="border-b border-line text-left text-xs text-muted">
              <tr><th className="px-4 py-3 font-medium">Received</th><th className="px-4 py-3 font-medium">Result</th><th className="px-4 py-3 text-right font-medium">NAV pts</th><th className="px-4 py-3 text-right font-medium">Investors</th><th className="px-4 py-3 text-right font-medium">Events</th><th className="px-4 py-3 font-medium">Payload</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {status?.runs.length === 0 && <tr><td colSpan={6} className="px-4 py-6 text-center text-muted">No syncs yet.</td></tr>}
              {status?.runs.map((r) => (
                <tr key={r.id} className="align-top">
                  <td className="whitespace-nowrap px-4 py-3">{dt(r.received_at)}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${r.status === 'applied' ? 'bg-accent-soft' : 'bg-warn-soft text-warn'}`}>{r.status}</span>
                    {r.message && <p className="mt-1 max-w-md break-words text-xs text-muted">{r.message}</p>}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">{r.nav_points}</td>
                  <td className="px-4 py-3 text-right font-mono">{r.investors}</td>
                  <td className="px-4 py-3 text-right font-mono">{r.events}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted">{r.payload_sha256}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
