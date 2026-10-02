import { Head } from 'vite-react-ssg'
import { Link } from 'react-router-dom'
import EligibilityGate from '../components/EligibilityGate'
import PageHeader from '../components/PageHeader'
import Ph from '../components/Ph'
import { site } from '../site.config'

const steps = [
  {
    title: 'Research',
    body: 'Ideas begin as hypotheses about how markets behave. Before anything else, each is written down as a complete set of rules — when a position is taken, how large it may be, and when it is closed — precise enough that anyone applying them would reach the same answer.',
  },
  {
    title: 'Testing',
    body: 'Rules are tested against historical data and examined for robustness: how they behave across different market conditions, how sensitive they are to small changes, and where they fail. Most are discarded. Testing is treated as a filter for weak ideas, not as a forecast of future results.',
  },
  {
    title: 'Risk',
    body: 'Position sizes and overall exposure are governed by limits that are set in advance and do not depend on recent performance. We do not increase risk to recover a loss.',
  },
  {
    title: 'Review and execution',
    body: 'Every trade is reviewed and signed off by a person before it is placed. The review checks that the data is sound and the order is what the rules intended; it is not an opportunity to override a valid signal on instinct. Where a trade is stopped, the reason is recorded.',
  },
  {
    title: 'Monitoring',
    body: 'Live results are compared against what testing led us to expect. When they diverge, we investigate before we intervene, and any change to a rule goes through the same written, tested process as a new one.',
  },
]

const infrastructure = [
  ['Broker', 'broker name'],
  ['Custody / depository participant', 'custodian or DP name'],
  ['Fund administration and accounting', 'administrator name'],
  ['Auditor', 'auditor name'],
  ['Legal counsel', 'counsel name'],
]

export function Component() {
  return (
    <>
      <Head>
        <title>{`Approach — ${site.name}`}</title>
        <meta name="description" content="A systematic, rules-based, research-driven investment process with human oversight." />
      </Head>
      <EligibilityGate>
        <PageHeader eyebrow="Approach" title="Systematic by design. Supervised by people.">
          We manage capital through a rules-based process. This page describes how that process is organised. It does not
          describe the rules themselves, which we keep confidential.
        </PageHeader>

        <section className="container-page py-8">
          <ol className="divide-y divide-line border-y border-line">
            {steps.map((s, i) => (
              <li key={s.title} className="grid gap-3 py-9 md:grid-cols-[4rem_14rem_1fr] md:gap-8">
                <span className="font-mono text-xs text-accent md:pt-1.5">{String(i + 1).padStart(2, '0')}</span>
                <h2 className="text-lg font-semibold tracking-tight">{s.title}</h2>
                <p className="max-w-prose text-[15.5px] leading-relaxed text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="container-page grid gap-12 py-20 lg:grid-cols-2">
          <div>
            <p className="eyebrow mb-3">What we do not publish</p>
            <h2 className="text-2xl font-semibold tracking-tight">Process, not prescriptions.</h2>
            <p className="mt-4 max-w-prose leading-relaxed text-muted">
              We do not publish the specifics of our rules, the signals they use, or performance information. Our
              process is the product of sustained research, and describing it in detail would weaken it. Existing
              investors receive reporting on their own holdings through a secure portal.
            </p>
          </div>
          <div>
            <p className="eyebrow mb-3">Operational infrastructure</p>
            <dl className="divide-y divide-line border-y border-line">
              {infrastructure.map(([k, v]) => (
                <div key={k} className="flex flex-col gap-1 py-4 sm:flex-row sm:justify-between">
                  <dt className="text-sm text-muted">{k}</dt>
                  <dd className="text-sm font-medium"><Ph>{v}</Ph></dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section className="container-page">
          <p className="max-w-prose text-[13px] leading-relaxed text-muted">
            This page is provided for information only. It is not an offer to sell, or a solicitation of an offer to
            buy, any security. Investing involves risk, including the loss of capital. See{' '}
            <Link to="/legal/risk" className="link">risk warnings</Link>.
          </p>
        </section>
      </EligibilityGate>
    </>
  )
}
