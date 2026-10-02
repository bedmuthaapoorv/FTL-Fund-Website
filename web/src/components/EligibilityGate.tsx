import { useEffect, useState, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { site } from '../site.config'
import { interstitial } from '../lib/content'
import Markdown from './Markdown'
import DraftBanner from './DraftBanner'

const KEY = 'fth-eligibility-ack'

/**
 * Click-through eligibility notice in front of pages that describe the
 * fund's offering/process. Gated content is never rendered on the server,
 * so it is absent from the statically generated HTML.
 */
export default function EligibilityGate({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const gated = site.interstitial.enabled && site.interstitial.protectedPaths.some((p) => pathname.startsWith(p))
  const [state, setState] = useState<'pending' | 'ack' | 'ask'>('pending')

  useEffect(() => {
    if (!gated) return setState('ack')
    let ok = false
    try { ok = sessionStorage.getItem(KEY) === '1' } catch { /* storage unavailable */ }
    setState(ok ? 'ack' : 'ask')
  }, [gated])

  if (!gated || state === 'ack') return <>{children}</>
  if (state === 'pending') return <div className="min-h-[60vh]" />

  const accept = () => {
    try { sessionStorage.setItem(KEY, '1') } catch { /* storage unavailable */ }
    setState('ack')
  }

  return (
    <section className="container-page py-16 sm:py-24">
      <div className="card mx-auto max-w-2xl p-6 sm:p-10" role="dialog" aria-modal="false" aria-labelledby="gate-title">
        <p className="eyebrow mb-4" id="gate-title">Important information</p>
        <DraftBanner className="mb-6" />
        <Markdown>{interstitial}</Markdown>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button type="button" className="btn-primary" onClick={accept}>{site.interstitial.acceptLabel}</button>
          <button type="button" className="btn-ghost" onClick={() => navigate('/')}>{site.interstitial.declineLabel}</button>
        </div>
      </div>
    </section>
  )
}
