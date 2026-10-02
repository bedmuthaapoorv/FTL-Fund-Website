import type { ReactNode } from 'react'

export default function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="container-page pb-10 pt-16 sm:pt-24">
      <p className="eyebrow mb-5">{eyebrow}</p>
      <h1 className="max-w-3xl text-[2.1rem] font-semibold leading-[1.12] tracking-tight sm:text-5xl">{title}</h1>
      {children && <div className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">{children}</div>}
    </div>
  )
}
