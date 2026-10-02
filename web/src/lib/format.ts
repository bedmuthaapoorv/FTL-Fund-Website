const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const num = (d: number) => new Intl.NumberFormat('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d })

export const fmtINR = (v: number) => inr.format(v)
export const fmtNum = (v: number, digits = 2) => num(digits).format(v)
export const fmtPct = (v: number | null) => (v === null ? '—' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${num(2).format(Math.abs(v))}%`)
export const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' }) =>
  new Date(iso.length === 10 ? iso + 'T00:00:00' : iso).toLocaleDateString('en-IN', opts)
