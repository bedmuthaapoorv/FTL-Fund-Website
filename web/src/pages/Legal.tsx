import { Head } from 'vite-react-ssg'
import { Link, useParams } from 'react-router-dom'
import DraftBanner from '../components/DraftBanner'
import Markdown from '../components/Markdown'
import { getLegal, legalOrder } from '../lib/content'
import { site } from '../site.config'
import { Component as NotFound } from './NotFound'

export function Component() {
  const { slug = '' } = useParams()
  const doc = getLegal(slug)
  if (!doc) return <NotFound />
  return (
    <div className="container-page grid gap-12 pt-16 sm:pt-24 lg:grid-cols-[14rem_1fr]">
      <Head>
        <title>{`${doc.meta.title} — ${site.name}`}</title>
      </Head>
      <nav aria-label="Legal" className="order-2 lg:order-1">
        <p className="eyebrow mb-4">Legal</p>
        <ul className="space-y-2.5 text-sm">
          {legalOrder.map((s) => (
            <li key={s}>
              <Link to={`/legal/${s}`} className={s === slug ? 'font-semibold text-ink' : 'text-muted hover:text-ink'}>
                {getLegal(s)?.meta.title}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="order-1 lg:order-2">
        <h1 className="mb-6 text-3xl font-semibold tracking-tight sm:text-4xl">{doc.meta.title}</h1>
        <DraftBanner className="mb-8 max-w-prose" />
        <Markdown>{doc.body}</Markdown>
      </div>
    </div>
  )
}
