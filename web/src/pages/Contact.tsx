import { useState, type FormEvent } from 'react'
import { Head } from 'vite-react-ssg'
import PageHeader from '../components/PageHeader'
import { api } from '../lib/api'
import { site } from '../site.config'

export function Component() {
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    setStatus('sending')
    try {
      await api('/contact', {
        body: {
          name: f.get('name'),
          email: f.get('email'),
          message: f.get('message'),
          website: f.get('website'), // honeypot
        },
      })
      setStatus('sent')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setStatus('error')
    }
  }

  return (
    <>
      <Head>
        <title>{`Contact — ${site.name}`}</title>
        <meta name="description" content="Get in touch with Frontier TradeLight." />
      </Head>
      <PageHeader eyebrow="Contact" title="Get in touch.">
        For enquiries, please use the form below or write to{' '}
        <a className="link" href={`mailto:${site.officialEmail}`}>{site.officialEmail}</a>.
      </PageHeader>

      <section className="container-page grid gap-12 lg:grid-cols-[1fr_20rem]">
        {status === 'sent' ? (
          <div className="card max-w-xl p-8" role="status">
            <h2 className="text-xl font-semibold tracking-tight">Thank you.</h2>
            <p className="mt-2 text-muted">Your message has been sent. We will reply by email.</p>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="max-w-xl space-y-5" noValidate={false}>
            <div>
              <label className="label" htmlFor="name">Name</label>
              <input className="field" id="name" name="name" required maxLength={120} autoComplete="name" />
            </div>
            <div>
              <label className="label" htmlFor="email">Email</label>
              <input className="field" id="email" name="email" type="email" required maxLength={254} autoComplete="email" />
            </div>
            <div>
              <label className="label" htmlFor="message">Message</label>
              <textarea className="field min-h-[160px]" id="message" name="message" required minLength={10} maxLength={4000} />
            </div>
            {/* Honeypot: hidden from people, filled in by naive bots. */}
            <div aria-hidden="true" className="absolute -left-[9999px] h-0 w-0 overflow-hidden">
              <label htmlFor="website">Website</label>
              <input id="website" name="website" tabIndex={-1} autoComplete="off" />
            </div>
            {status === 'error' && <p role="alert" className="text-sm text-warn">{error}</p>}
            <button className="btn-primary" disabled={status === 'sending'}>
              {status === 'sending' ? 'Sending…' : 'Send message'}
            </button>
          </form>
        )}

        <aside className="space-y-4 text-sm leading-relaxed text-muted">
          <p>Please do not include account numbers, identity documents or other sensitive information in your message.</p>
          <p>
            Messages are delivered to us by email and are not stored on this website. See our{' '}
            <a className="link" href="/legal/privacy">privacy policy</a>.
          </p>
        </aside>
      </section>
    </>
  )
}
