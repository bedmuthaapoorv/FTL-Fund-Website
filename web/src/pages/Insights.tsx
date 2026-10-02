import { Head } from 'vite-react-ssg'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import { formatDate, insights } from '../lib/content'
import { site } from '../site.config'

export function Component() {
  return (
    <>
      <Head>
        <title>{`Insights — ${site.name}`}</title>
        <meta name="description" content="Short essays on research discipline, risk and process." />
      </Head>
      <PageHeader eyebrow="Insights" title="Notes on process.">
        Occasional essays on research discipline, risk and the practice of systematic investing.
      </PageHeader>
      <section className="container-page">
        <ul className="divide-y divide-line border-y border-line">
          {insights.map((a) => (
            <li key={a.slug}>
              <Link to={`/insights/${a.slug}`} className="group grid gap-2 py-8 sm:grid-cols-[10rem_1fr] sm:gap-8">
                <span className="font-mono text-xs text-muted sm:pt-1.5">{formatDate(a.meta.date)}</span>
                <span>
                  <span className="flex flex-wrap items-center gap-2 text-xl font-semibold tracking-tight group-hover:text-accent">
                    {a.meta.title}
                    {a.meta.draft === 'true' && <span className="placeholder-tag text-[11px] font-normal">DRAFT</span>}
                  </span>
                  <span className="mt-1.5 block max-w-prose text-[15px] leading-relaxed text-muted">{a.meta.summary}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
