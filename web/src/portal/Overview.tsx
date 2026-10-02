import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { api } from '../lib/api'
import type { Me } from '../lib/auth'
import { fmtDate, fmtINR, fmtNum, fmtPct } from '../lib/format'
import Ph from '../components/Ph'
import NavChart, { type NavPoint } from './NavChart'

type Summary = {
  linked: boolean
  units: number
  nav: number
  current_value: number
  total_deposited: number
  total_withdrawn: number
  net_contributed: number
  return_pct: number | null
  first_investment: string | null
  as_of: string | null
}
type Event = { id: number; date: string; type: 'DEPOSIT' | 'WITHDRAWAL'; amount: number; nav: number; units: number }

function Tile({ label, value, sub, hero = false }: { label: string; value: string; sub?: string; hero?: boolean }) {
  return (
    <div className="card p-4 sm:p-5">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className={`mt-2 font-mono font-medium tracking-tight text-ink ${hero ? 'text-xl sm:text-3xl' : 'text-xl sm:text-2xl'}`}>{value}</p>
      {sub && <p className="mt-1.5 text-[11px] leading-snug text-muted sm:text-xs">{sub}</p>}
    </div>
  )
}

export function Component() {
  const me = useOutletContext<Me>()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [nav, setNav] = useState<NavPoint[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api<Summary>('/me/summary'),
      api<Event[]>('/me/events'),
      api<{ points: NavPoint[] }>('/fund/nav'),
    ])
      .then(([s, e, n]) => { setSummary(s); setEvents(e); setNav(n.points) })
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <div className="container-page text-sm text-warn">{error}</div>
  if (!summary) return <div className="container-page text-sm text-muted">Loading…</div>

  const name = me.display_name || me.email

  return (
    <div className="container-page space-y-10">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow mb-2">Your investment</p>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{name}</h1>
        </div>
        {summary.as_of && <p className="text-xs text-muted">Data as of {fmtDate(summary.as_of)}</p>}
      </div>

      {!summary.linked ? (
        <div className="card max-w-2xl p-6 sm:p-8">
          <h2 className="text-lg font-semibold">Your account is ready.</h2>
          <p className="mt-2 text-muted">
            Your holding will appear here once it has been linked to your account. If you expected to see it already,
            please contact us.
          </p>
        </div>
      ) : (
        <>
          <section aria-label="Position" className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <Tile hero label="Current value" value={fmtINR(summary.current_value)} sub={`At NAV ${fmtNum(summary.nav)} per unit`} />
            <Tile label="Units held" value={fmtNum(summary.units, 4)} />
            <Tile
              label="Net capital contributed"
              value={fmtINR(summary.net_contributed)}
              sub={`${fmtINR(summary.total_deposited)} in · ${fmtINR(summary.total_withdrawn)} out`}
            />
            <Tile
              label="Return since inception"
              value={fmtPct(summary.return_pct)}
              sub={summary.first_investment ? `On net capital, since ${fmtDate(summary.first_investment)}` : undefined}
            />
          </section>

          <section className="card p-5 sm:p-7" aria-labelledby="nav-title">
            <div className="mb-5">
              <h2 id="nav-title" className="text-base font-semibold">Fund NAV per unit</h2>
              <p className="mt-1 text-xs text-muted">Units were first issued at 100. Values are net of <Ph>fees/expenses basis</Ph>.</p>
            </div>
            <NavChart points={nav} />
          </section>

          <section aria-labelledby="hist-title">
            <h2 id="hist-title" className="mb-4 text-base font-semibold">Contribution history</h2>
            {events.length === 0 ? (
              <p className="text-sm text-muted">No deposits or withdrawals recorded.</p>
            ) : (
              <div className="card overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="border-b border-line text-left text-xs text-muted">
                    <tr>
                      <th className="px-5 py-3 font-medium">Date</th>
                      <th className="px-5 py-3 font-medium">Type</th>
                      <th className="px-5 py-3 text-right font-medium">Amount</th>
                      <th className="px-5 py-3 text-right font-medium">NAV</th>
                      <th className="px-5 py-3 text-right font-medium">Units</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {[...events].reverse().map((e) => (
                      <tr key={e.id}>
                        <td className="whitespace-nowrap px-5 py-3">{fmtDate(e.date)}</td>
                        <td className="px-5 py-3">{e.type === 'DEPOSIT' ? 'Deposit' : 'Withdrawal'}</td>
                        <td className="px-5 py-3 text-right font-mono">{fmtINR(e.amount)}</td>
                        <td className="px-5 py-3 text-right font-mono">{fmtNum(e.nav)}</td>
                        <td className="px-5 py-3 text-right font-mono">{e.units > 0 ? '+' : '−'}{fmtNum(Math.abs(e.units), 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      <p className="max-w-prose text-xs leading-relaxed text-muted">
        Return since inception is the gain on your net capital contributed (deposits less withdrawals), valued at the
        latest recorded NAV. It is not annualised and does not account for the timing of contributions. These figures
        are unaudited; your official statements prevail. Past performance is not indicative of future results.
      </p>
    </div>
  )
}
