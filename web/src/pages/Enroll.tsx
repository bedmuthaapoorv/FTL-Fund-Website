import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthCard, { FormError } from '../components/AuthCard'
import { api } from '../lib/api'
import { homeFor, type Me } from '../lib/auth'

type Setup = { secret: string; uri: string; qr_svg: string }

export function Component() {
  const navigate = useNavigate()
  const [setup, setSetup] = useState<Setup | null>(null)
  const [codes, setCodes] = useState<string[] | null>(null)
  const [role, setRole] = useState<Me['role']>('investor')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api<Setup>('/auth/mfa/setup').then(setSetup).catch(() => setError('expired'))
  }, [])

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    api<{ recovery_codes: string[]; role: Me['role'] }>('/auth/mfa/enroll', { body: { code: new FormData(e.currentTarget).get('code') } })
      .then((r) => { setCodes(r.recovery_codes); setRole(r.role) })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }

  if (error === 'expired') {
    return (
      <AuthCard title="Session expired">
        <p className="text-sm text-muted">Please <Link className="link" to="/login">sign in again</Link> to continue setting up two-step verification.</p>
      </AuthCard>
    )
  }

  if (codes) {
    return (
      <AuthCard title="Save your recovery codes">
        <p className="text-sm text-muted">
          If you lose access to your authenticator app, each of these codes lets you sign in once. Store them somewhere
          safe, such as a password manager. They will not be shown again.
        </p>
        <ul className="my-5 grid grid-cols-2 gap-2 rounded-lg border border-line bg-ground p-4 font-mono text-sm">
          {codes.map((c) => <li key={c}>{c}</li>)}
        </ul>
        <button type="button" className="btn-ghost mb-5 w-full" onClick={() => void navigator.clipboard?.writeText(codes.join('\n'))}>
          Copy codes
        </button>
        <label className="mb-5 flex items-start gap-2.5 text-sm">
          <input type="checkbox" className="mt-0.5 accent-[rgb(var(--accent))]" checked={saved} onChange={(e) => setSaved(e.target.checked)} />
          I have saved these codes somewhere safe.
        </label>
        <button className="btn-primary w-full" disabled={!saved} onClick={() => navigate(homeFor(role), { replace: true })}>Continue</button>
      </AuthCard>
    )
  }

  return (
    <AuthCard title="Set up two-step verification">
      {!setup ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-5">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-muted">
            <li>Open an authenticator app (for example Google Authenticator, Microsoft Authenticator or 1Password).</li>
            <li>Scan this code, or enter the key manually.</li>
            <li>Enter the 6-digit code the app shows.</li>
          </ol>
          {/* Server-generated SVG (segno) encoding the user's own otpauth URI. */}
          <div className="mx-auto w-48 overflow-hidden rounded-lg border border-line bg-white p-1 [&>svg]:h-auto [&>svg]:w-full" dangerouslySetInnerHTML={{ __html: setup.qr_svg }} />
          <p className="break-all text-center font-mono text-xs text-muted">{setup.secret.match(/.{1,4}/g)?.join(' ')}</p>
          <div>
            <label className="label" htmlFor="code">Code</label>
            <input className="field font-mono tracking-[0.2em]" id="code" name="code" required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9 ]{6,7}" maxLength={7} placeholder="123456" />
          </div>
          <FormError>{error}</FormError>
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Verifying…' : 'Turn on two-step verification'}</button>
        </form>
      )}
    </AuthCard>
  )
}
