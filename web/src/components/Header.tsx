import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { nav } from '../site.config'
import Logo from './Logo'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => setOpen(false), [pathname])

  const linkCls = ({ isActive }: { isActive: boolean }) =>
    `text-sm font-medium transition-colors ${isActive ? 'text-ink' : 'text-muted hover:text-ink'}`

  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-ground/85 backdrop-blur-md">
      <div className="container-page flex h-16 items-center justify-between">
        <Link to="/" className="text-ink no-underline" aria-label="Frontier TradeLight, home">
          <Logo />
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-8 md:flex">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} className={linkCls}>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <Link to="/login" className="btn-ghost hidden !py-2 sm:inline-flex">
            Investor login
          </Link>
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-md text-ink md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen((o) => !o)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
              {open ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Main" className="border-t border-line bg-ground md:hidden">
          <div className="container-page flex flex-col py-2">
            {nav.map((n) => (
              <NavLink key={n.to} to={n.to} className={({ isActive }) => `py-3 text-base font-medium ${isActive ? 'text-ink' : 'text-muted'}`}>
                {n.label}
              </NavLink>
            ))}
            <Link to="/login" className="btn-ghost my-3">
              Investor login
            </Link>
          </div>
        </nav>
      )}
    </header>
  )
}
