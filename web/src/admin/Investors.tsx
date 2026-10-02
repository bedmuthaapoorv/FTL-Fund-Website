import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { FormError } from '../components/AuthCard'
import { api } from '../lib/api'
import { fmtDate, fmtINR, fmtNum } from '../lib/format'

type User = {
  id: number; email: string; display_name: string; role: 'investor' | 'admin'; status: 'invited' | 'active' | 'disabled'
  investor_id: string | null; mfa_enabled: boolean; last_login_at: string | null
}
type SyncedId = { investor_id: string; units: number; current_value: number; linked_to: string | null }

const statusStyle: Record<User['status'], string> = {
  active: 'bg-accent-soft text-ink',
  invited: 'bg-warn-soft text-warn',
  disabled: 'bg-line text-muted',
}

function InviteLink({ link, onClose }: { link: string; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  return (
    <div role="status" className="rounded-lg border border-accent/30 bg-accent-soft p-4">
      <p className="text-sm font-semibold">Invitation link created</p>
      <p className="mt-1 text-xs text-muted">Send it from your official email address. It works once and expires in 72 hours. It is not stored and will not be shown again.</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <input readOnly value={link} className="field font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
        <button className="btn-primary" onClick={() => { void navigator.clipboard?.writeText(link); setCopied(true) }}>{copied ? 'Copied' : 'Copy'}</button>
        <button className="btn-ghost" onClick={onClose}>Done</button>
      </div>
    </div>
  )
}

export function Component() {
  const [users, setUsers] = useState<User[]>([])
  const [ids, setIds] = useState<SyncedId[]>([])
  const [link, setLink] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const [u, i] = await Promise.all([api<User[]>('/admin/users'), api<SyncedId[]>('/admin/investor-ids')])
    setUsers(u)
    setIds(i)
  }, [])
  useEffect(() => { load().catch((e) => setError(e.message)) }, [load])

  const act = async (fn: () => Promise<unknown>) => {
    setError('')
    try { await fn(); await load() } catch (e) { setError(e instanceof Error ? e.message : 'Failed.') }
  }

  const unlinkedIds = ids.filter((i) => !i.linked_to)

  const onCreate = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const f = new FormData(form)
    setBusy(true)
    void act(async () => {
      const r = await api<{ invite_link: string }>('/admin/users', {
        body: { email: f.get('email'), display_name: f.get('display_name'), investor_id: f.get('investor_id') || null },
      })
      setLink(r.invite_link)
      form.reset()
    }).finally(() => setBusy(false))
  }

  const relink = (u: User, investor_id: string) =>
    act(() => api(`/admin/users/${u.id}`, { method: 'PATCH', body: investor_id ? { investor_id } : { unlink: true } }))

  const toggle = (u: User) => {
    const next = u.status === 'disabled' ? 'active' : 'disabled'
    if (next === 'disabled' && !confirm(`Disable ${u.email}? They will be signed out immediately.`)) return
    void act(() => api(`/admin/users/${u.id}`, { method: 'PATCH', body: { status: next } }))
  }

  const reset = (u: User) => {
    if (!confirm(`Reset access for ${u.email}? Their password, two-step verification and sessions are revoked, and a new invitation link is created.`)) return
    void act(async () => setLink((await api<{ invite_link: string }>(`/admin/users/${u.id}/reset-access`, { method: 'POST' })).invite_link))
  }

  return (
    <div className="container-page space-y-10">
      <div>
        <p className="eyebrow mb-2">Admin</p>
        <h1 className="text-2xl font-semibold tracking-tight">Investors</h1>
      </div>

      {link && <InviteLink link={link} onClose={() => setLink(null)} />}
      <FormError>{error}</FormError>

      <section className="card p-5 sm:p-6" aria-labelledby="invite-title">
        <h2 id="invite-title" className="text-base font-semibold">Invite an investor</h2>
        <p className="mt-1 text-sm text-muted">Accounts are invitation-only. Link the account to a synced investor ID now or later.</p>
        <form onSubmit={onCreate} className="mt-5 grid gap-4 md:grid-cols-[1fr_1fr_1fr_auto] md:items-end">
          <div><label className="label" htmlFor="email">Email</label><input className="field" id="email" name="email" type="email" required /></div>
          <div><label className="label" htmlFor="display_name">Display name</label><input className="field" id="display_name" name="display_name" maxLength={120} /></div>
          <div>
            <label className="label" htmlFor="investor_id">Investor ID</label>
            <select className="field" id="investor_id" name="investor_id" defaultValue="">
              <option value="">Link later</option>
              {unlinkedIds.map((i) => <option key={i.investor_id} value={i.investor_id}>{i.investor_id}</option>)}
            </select>
          </div>
          <button className="btn-primary" disabled={busy}>Create invitation</button>
        </form>
      </section>

      <section aria-labelledby="accounts-title">
        <h2 id="accounts-title" className="mb-4 text-base font-semibold">Accounts</h2>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead className="border-b border-line text-left text-xs text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Account</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Investor ID</th>
                <th className="px-4 py-3 font-medium">Last sign-in</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{u.display_name || u.email}</div>
                    <div className="text-xs text-muted">{u.email}{u.role === 'admin' && ' · admin'}{u.mfa_enabled ? ' · 2FA on' : ''}</div>
                  </td>
                  <td className="px-4 py-3"><span className={`rounded px-2 py-0.5 text-xs font-medium ${statusStyle[u.status]}`}>{u.status}</span></td>
                  <td className="px-4 py-3">
                    {u.role === 'investor' ? (
                      <select
                        aria-label={`Investor ID for ${u.email}`}
                        className="field !py-1.5 font-mono text-xs"
                        value={u.investor_id ?? ''}
                        onChange={(e) => void relink(u, e.target.value)}
                      >
                        <option value="">Not linked</option>
                        {u.investor_id && !ids.some((i) => i.investor_id === u.investor_id) && <option value={u.investor_id}>{u.investor_id} (not in latest sync)</option>}
                        {ids.filter((i) => !i.linked_to || i.investor_id === u.investor_id).map((i) => (
                          <option key={i.investor_id} value={i.investor_id}>{i.investor_id}</option>
                        ))}
                      </select>
                    ) : <span className="text-muted">—</span>}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted">{u.last_login_at ? fmtDate(u.last_login_at) : 'Never'}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    {u.role === 'investor' && (
                      <>
                        {u.status !== 'invited' && (
                          <button className="mr-3 text-xs font-medium text-muted hover:text-ink" onClick={() => toggle(u)}>{u.status === 'disabled' ? 'Enable' : 'Disable'}</button>
                        )}
                        <button className="text-xs font-medium text-muted hover:text-ink" onClick={() => reset(u)}>{u.status === 'invited' ? 'New invite link' : 'Reset access'}</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="ids-title">
        <h2 id="ids-title" className="mb-1 text-base font-semibold">Synced investor IDs</h2>
        <p className="mb-4 text-sm text-muted">Pseudonymous IDs from the latest FrontierTradeLight sync. Run the export script with <code className="font-mono text-xs">--show-ids</code> on your machine to see which is which.</p>
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="border-b border-line text-left text-xs text-muted">
              <tr><th className="px-4 py-3 font-medium">Investor ID</th><th className="px-4 py-3 text-right font-medium">Units</th><th className="px-4 py-3 text-right font-medium">Value</th><th className="px-4 py-3 font-medium">Linked account</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {ids.length === 0 && <tr><td colSpan={4} className="px-4 py-6 text-center text-muted">No data synced yet.</td></tr>}
              {ids.map((i) => (
                <tr key={i.investor_id}>
                  <td className="px-4 py-3 font-mono text-xs">{i.investor_id}</td>
                  <td className="px-4 py-3 text-right font-mono">{fmtNum(i.units, 4)}</td>
                  <td className="px-4 py-3 text-right font-mono">{fmtINR(i.current_value)}</td>
                  <td className="px-4 py-3">{i.linked_to ?? <span className="text-warn">Not linked</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
