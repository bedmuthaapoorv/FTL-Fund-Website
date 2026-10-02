import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthCard, { FormError } from '../components/AuthCard'
import { api } from '../lib/api'
import { homeFor, useMe, type Me } from '../lib/auth'

export function Component() {
  const navigate = useNavigate()
  const { me } = useMe()
  const [step, setStep] = useState<'password' | 'mfa'>('password')
  const [useRecovery, setUseRecovery] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // Already signed in (or mid-login after a refresh): resume where they were.
  useEffect(() => {
    if (!me) return
    if (me.stage === 'full') navigate(homeFor(me.role), { replace: true })
    else if (me.stage === 'enroll') navigate('/enroll', { replace: true })
    else setStep('mfa')
  }, [me, navigate])

  async function run(fn: () => Promise<void>) {
    setBusy(true)
    setError('')
    try { await fn() } catch (e) { setError(e instanceof Error ? e.message : 'Something went wrong.') } finally { setBusy(false) }
  }

  const onPassword = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    void run(async () => {
      const r = await api<{ next: 'mfa' | 'enroll' }>('/auth/login', { body: { email: f.get('email'), password: f.get('password') } })
      if (r.next === 'enroll') navigate('/enroll')
      else setStep('mfa')
    })
  }

  const onCode = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const v = String(new FormData(e.currentTarget).get('code') ?? '')
    void run(async () => {
      const r = await api<{ role: Me['role']; recovery_codes_remaining: number }>('/auth/mfa/verify', {
        body: useRecovery ? { recovery_code: v } : { code: v },
      })
      navigate(homeFor(r.role), { replace: true })
    })
  }

  if (step === 'mfa') {
    return (
      <AuthCard title="Two-step verification">
        <form onSubmit={onCode} className="space-y-5">
          <p className="text-sm text-muted">
            {useRecovery ? 'Enter one of your recovery codes. Each code works once.' : 'Enter the 6-digit code from your authenticator app.'}
          </p>
          <div>
            <label className="label" htmlFor="code">{useRecovery ? 'Recovery code' : 'Code'}</label>
            <input
              key={String(useRecovery)}
              className="field font-mono tracking-[0.2em]"
              id="code" name="code" required autoFocus
              autoComplete="one-time-code"
              inputMode={useRecovery ? 'text' : 'numeric'}
              pattern={useRecovery ? undefined : '[0-9 ]{6,7}'}
              maxLength={useRecovery ? 12 : 7}
              placeholder={useRecovery ? 'XXXXX-XXXXX' : '123456'}
            />
          </div>
          <FormError>{error}</FormError>
          <button className="btn-primary w-full" disabled={busy}>{busy ? 'Verifying…' : 'Verify'}</button>
          <button type="button" className="w-full text-sm text-muted hover:text-ink" onClick={() => { setUseRecovery((v) => !v); setError('') }}>
            {useRecovery ? 'Use authenticator code instead' : 'Lost your device? Use a recovery code'}
          </button>
        </form>
      </AuthCard>
    )
  }

  return (
    <AuthCard title="Sign in">
      <form onSubmit={onPassword} className="space-y-5">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input className="field" id="email" name="email" type="email" required autoComplete="username" autoFocus />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input className="field" id="password" name="password" type="password" required autoComplete="current-password" />
        </div>
        <FormError>{error}</FormError>
        <button className="btn-primary w-full" disabled={busy || me === undefined}>{busy ? 'Signing in…' : 'Continue'}</button>
        <p className="text-xs leading-relaxed text-muted">
          Access is by invitation only. After several failed attempts, sign-in is paused for 15 minutes. If you have lost
          access, contact us and we will send a new invitation.
        </p>
      </form>
    </AuthCard>
  )
}
