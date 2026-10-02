import { Head } from 'vite-react-ssg'
import { Link } from 'react-router-dom'
import ContourField from '../components/ContourField'
import Ph from '../components/Ph'
import { formatDate, insights } from '../lib/content'
import { site } from '../site.config'

const principles = [
  {
    n: '01',
    title: 'Rules, written down',
    body: 'Every idea is stated precisely enough to be tested before it is used. Most do not survive testing, which is the point.',
  },
  {
    n: '02',
    title: 'Risk decided in advance',
    body: 'Position sizes and exposure limits are set before a trade is taken, and do not change in response to recent results.',
  },
  {
    n: '03',
    title: 'A person signs off',
    body: 'Every trade is reviewed by a human before it is placed. The review checks the inputs and the order, not the conviction.',
  },
]

export function Component() {
  return (
    <>
      <Head>
        <title>{site.name}</title>
        <meta name="description" content="Frontier TradeLight is a systematic, research-driven investment manager." />
      </Head>

      <section className="relative overflow-hidden">
        <ContourField className="pointer-events-none absolute opacity-50 sm:opacity-100 -right-48 -top-24 h-[640px] w-[640px] text-accent sm:-right-24 lg:right-0 lg:top-[-40px] lg:h-[720px] lg:w-[720px]" />
        <div className="container-page relative pb-24 pt-20 sm:pb-32 sm:pt-32">
          <p className="eyebrow mb-6">Systematic investment management</p>
          <h1 className="max-w-3xl text-[2.4rem] font-semibold leading-[1.08] tracking-tight sm:text-6xl">
            Disciplined investing, governed by written rules.
          </h1>
          <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted">
            {site.name} is a <Ph>legal structure</Ph> that manages capital through a systematic, research-driven
            process. Rules are written and tested before they are used, risk is set in advance, and every trade is
            reviewed by a person before it is placed.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link to="/approach" className="btn-primary">Our approach</Link>
            <Link to="/contact" className="btn-ghost">Contact us</Link>
          </div>
        </div>
      </section>

      <section className="border-y border-line bg-surface/60">
        <div className="container-page grid gap-px py-4 sm:grid-cols-3">
          {principles.map((p) => (
            <div key={p.n} className="py-8 sm:px-6 sm:first:pl-0 sm:last:pr-0">
              <p className="font-mono text-xs text-accent">{p.n}</p>
              <h2 className="mt-3 text-lg font-semibold tracking-tight">{p.title}</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-muted">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="container-page py-24">
        <div className="flex items-end justify-between gap-6">
          <div>
            <p className="eyebrow mb-3">Insights</p>
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">Notes on process</h2>
          </div>
          <Link to="/insights" className="link hidden text-sm sm:inline">All insights</Link>
        </div>
        <ul className="mt-10 divide-y divide-line border-y border-line">
          {insights.slice(0, 3).map((a) => (
            <li key={a.slug}>
              <Link to={`/insights/${a.slug}`} className="group grid gap-2 py-6 sm:grid-cols-[10rem_1fr] sm:gap-8">
                <span className="font-mono text-xs text-muted sm:pt-1.5">{formatDate(a.meta.date)}</span>
                <span>
                  <span className="block text-lg font-semibold tracking-tight group-hover:text-accent">{a.meta.title}</span>
                  <span className="mt-1 block text-[15px] text-muted">{a.meta.summary}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="container-page">
        <div className="card flex flex-col items-start justify-between gap-6 p-8 sm:flex-row sm:items-center sm:p-10">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">We prefer direct conversations.</h2>
            <p className="mt-1.5 text-muted">If you would like to learn more, please get in touch.</p>
          </div>
          <Link to="/contact" className="btn-primary">Contact us</Link>
        </div>
      </section>
    </>
  )
}
