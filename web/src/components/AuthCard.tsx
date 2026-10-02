import type { ReactNode } from 'react'
import { Head } from 'vite-react-ssg'

/** Narrow centred card used by every sign-in/enrolment step. */
export default function AuthCard({ title, eyebrow = 'Investor portal', children }: { title: string; eyebrow?: string; children: ReactNode }) {
  return (
    <section className="container-page flex min-h-[70vh] items-start justify-center py-16 sm:py-24">
      <Head><title>{title}</title><meta name="robots" content="noindex" /></Head>
      <div className="card w-full max-w-md p-6 sm:p-9">
        <p className="eyebrow mb-3">{eyebrow}</p>
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">{title}</h1>
        {children}
      </div>
    </section>
  )
}

export function FormError({ children }: { children?: ReactNode }) {
  if (!children) return null
  return <p role="alert" className="rounded-md bg-warn-soft px-3 py-2 text-sm text-warn">{children}</p>
}
