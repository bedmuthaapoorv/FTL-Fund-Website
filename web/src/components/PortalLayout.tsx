import { useEffect } from 'react'
import { Head } from 'vite-react-ssg'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { homeFor, logout, useMe, type Me } from '../lib/auth'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'

type NavItem = { label: string; to: string; end?: boolean }

const NAV: Record<Me['role'], NavItem[]> = {
  investor: [{ label: 'Overview', to: '/portal', end: true }],
  admin: [
    { label: 'Investors', to: '/admin', end: true },
    { label: 'Data sync', to: '/admin/sync' },
    { label: 'Audit log', to: '/admin/audit' },
  ],
}

/** Shell for authenticated areas. The server enforces access on every API
 * call; this guard only decides what to render. */
export default function PortalLayout({ role }: { role: Me['role'] }) {
  const navigate = useNavigate()
  const { me } = useMe()

  useEffect(() => {
    if (me === undefined) return
    if (me === null || me.stage !== 'full') navigate('/login', { replace: true })
    else if (me.role !== role) navigate(homeFor(me.role), { replace: true })
  }, [me, role, navigate])

  const signOut = async () => {
    await logout().catch(() => undefined)
    navigate('/login', { replace: true })
  }

  const ready = me && me.stage === 'full' && me.role === role

  return (
    <div className="flex min-h-screen flex-col">
      <Head><title>{role === 'admin' ? 'Admin' : 'Investor portal'}</title><meta name="robots" content="noindex" /></Head>
      <header className="border-b border-line bg-surface">
        <div className="container-page flex h-14 items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-6">
            <Link to={homeFor(role)} className="text-ink"><Logo compact /></Link>
            <nav className="flex gap-5 overflow-x-auto text-sm">
              {NAV[role].map((n) => (
                <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `whitespace-nowrap py-4 font-medium ${isActive ? 'text-ink shadow-[inset_0_-2px_0_rgb(var(--accent))]' : 'text-muted hover:text-ink'}`}>
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex flex-shrink-0 items-center gap-1">
            {ready && <span className="mr-2 hidden text-sm text-muted md:inline">{me.email}</span>}
            <ThemeToggle />
            <button type="button" onClick={signOut} className="rounded-md px-2.5 py-1.5 text-sm font-medium text-muted hover:text-ink">Sign out</button>
          </div>
        </div>
      </header>
      <main className="flex-1 py-10">
        {ready ? <Outlet context={me} /> : <div className="container-page text-sm text-muted">Loading…</div>}
      </main>
      <footer className="border-t border-line py-6">
        <p className="container-page text-xs leading-relaxed text-muted">
          Confidential. For the named investor only. Figures are unaudited and provided for information; your official
          statements prevail. Past performance is not indicative of future results.{' '}
          <span className="placeholder-tag">[PLACEHOLDER: counsel to confirm portal disclaimer]</span>
        </p>
      </footer>
    </div>
  )
}
