import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthCard, { FormError } from '../components/AuthCard'
import { api } from '../lib/api'

export function Component() {
  const navigate = useNavigate()
  const [token, setToken] = useState<string | null>(null)
  const [email, setEmail] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    // The token travels in the URL fragment so it never reaches server logs.
    const t = new URLSearchParams(window.location.hash.slice(1)).get('token')
    history.replaceState(null, '', window.location.pathname)
    if (!t) return setError('This invitation link is incomplete.')
    setToken(t)
    api<{ email: string }>('/auth/invite/check', { body: { token: t } })
      .then((r) => setEmail(r.email))
      .catch((e) => setError(e.message))
  }, [])

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    if (f.get('password') !== f.get('confirm')) return setError('The passwords do not match.')
    setBusy(true)
    setError('')
    api('/auth/invite/accept', { body: { token, password: f.get('password') } })
      .then(() => navigate('/enroll', { replace: true }))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }

  return (
    <AuthCard title="Set up your account">
      {email ? (
        <form onSubmit={onSubmit} className="space-y-5">
          <p className="text-sm text-muted">
            Choose a password for <span className="font-medium text-ink">{email}</span>. Next, you will set up two-step
            verification.
          </p>
          <input type="email" value={email} autoComplete="username" readOnly hidden />
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input className="field" id="password" name="password" type="password" required minLength={12} autoComplete="new-password" />
            <p className="mt-1.5 text-xs text-muted">At least 12 characters. A passphrase of several words works well.</p>
          </div>
          <div>
            <label className="label" htmlFor="confirm">Confirm password</label>
            <input className="field" id="confirm" name="confirm" type="password" required minLength={12} autoComplete="new-password" />
          </div>
          <FormError>{error}</FormError>
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Saving…' : 'Continue'}</button>
        </form>
      ) : (
        <>{error ? <FormError>{error}</FormError> : <p className="text-sm text-muted">Checking your invitation…</p>}</>
      )}
    </AuthCard>
  )
}
