import { Head } from 'vite-react-ssg'
import PageHeader from '../components/PageHeader'
import Ph from '../components/Ph'
import { site } from '../site.config'
import { Component as NotFound } from './NotFound'

// Hidden until site.features.team is enabled; content to be supplied.
export function Component() {
  if (!site.features.team) return <NotFound />
  return (
    <>
      <Head><title>{`Team — ${site.name}`}</title></Head>
      <PageHeader eyebrow="Team" title="People">
        <Ph>team introduction</Ph>
      </PageHeader>
      <section className="container-page">
        <div className="card max-w-2xl p-8">
          <h2 className="text-xl font-semibold"><Ph>founder name</Ph></h2>
          <p className="mt-1 text-sm text-muted"><Ph>title</Ph></p>
          <p className="mt-4 leading-relaxed text-muted"><Ph>background, education, credentials, years in markets</Ph></p>
        </div>
      </section>
    </>
  )
}
