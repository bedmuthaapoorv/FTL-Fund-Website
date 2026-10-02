import { Head } from 'vite-react-ssg'
import { Link, useParams } from 'react-router-dom'
import Markdown from '../components/Markdown'
import { formatDate, getInsight } from '../lib/content'
import { site } from '../site.config'
import { Component as NotFound } from './NotFound'

export function Component() {
  const { slug = '' } = useParams()
  const doc = getInsight(slug)
  if (!doc) return <NotFound />
  return (
    <article className="container-page pt-16 sm:pt-24">
      <Head>
        <title>{`${doc.meta.title} — ${site.name}`}</title>
        <meta name="description" content={doc.meta.summary} />
      </Head>
      <Link to="/insights" className="text-sm text-muted hover:text-ink">← Insights</Link>
      <header className="mb-10 mt-8 max-w-prose">
        <p className="font-mono text-xs text-muted">
          {formatDate(doc.meta.date)}
          {doc.meta.draft === 'true' && <span className="placeholder-tag ml-3">DRAFT</span>}
        </p>
        <h1 className="mt-4 text-[2rem] font-semibold leading-tight tracking-tight sm:text-[2.6rem]">{doc.meta.title}</h1>
        <p className="mt-4 text-lg leading-relaxed text-muted">{doc.meta.summary}</p>
      </header>
      <Markdown>{doc.body}</Markdown>
    </article>
  )
}
