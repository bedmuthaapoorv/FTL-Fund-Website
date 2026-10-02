import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react'
import { fmtDate, fmtNum } from '../lib/format'

export type NavPoint = { date: string; nav: number; generation: number }

const RANGES = [
  { key: '6M', months: 6 },
  { key: '1Y', months: 12 },
  { key: 'All', months: 0 },
] as const
type RangeKey = (typeof RANGES)[number]['key']

const H = 260
const M = { top: 16, right: 16, bottom: 28, left: 52 }

function niceTicks(min: number, max: number, count = 4) {
  const span = max - min || 1
  const raw = span / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw
  const lo = Math.floor(min / step) * step
  const hi = Math.ceil(max / step) * step
  const ticks: number[] = []
  for (let v = lo; v <= hi + step / 2; v += step) ticks.push(+v.toFixed(10))
  return { lo, hi, ticks }
}

/** Single-series fund NAV line. Each fund "generation" (era after a full
 * wind-down) is drawn as its own segment, never joined to the next. */
export default function NavChart({ points }: { points: NavPoint[] }) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(640)
  const [range, setRange] = useState<RangeKey>('1Y')
  const [hover, setHover] = useState<number | null>(null)
  const [showTable, setShowTable] = useState(false)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const data = useMemo(() => {
    const months = RANGES.find((r) => r.key === range)!.months
    if (!months || !points.length) return points
    const cutoff = new Date(points[points.length - 1].date + 'T00:00:00')
    cutoff.setMonth(cutoff.getMonth() - months)
    const iso = cutoff.toISOString().slice(0, 10)
    return points.filter((p) => p.date >= iso)
  }, [points, range])

  useEffect(() => setHover(null), [range])

  const geo = useMemo(() => {
    if (data.length < 2) return null
    const t = data.map((p) => new Date(p.date + 'T00:00:00').getTime())
    const vals = data.map((p) => p.nav)
    const { lo, hi, ticks } = niceTicks(Math.min(...vals), Math.max(...vals))
    const iw = width - M.left - M.right
    const ih = H - M.top - M.bottom
    const x = (i: number) => M.left + ((t[i] - t[0]) / (t[t.length - 1] - t[0])) * iw
    const y = (v: number) => M.top + (1 - (v - lo) / (hi - lo)) * ih

    const segments: { line: string; area: string }[] = []
    let start = 0
    for (let i = 1; i <= data.length; i++) {
      if (i === data.length || data[i].generation !== data[start].generation) {
        const idx = Array.from({ length: i - start }, (_, k) => start + k)
        const line = idx.map((j, k) => `${k ? 'L' : 'M'}${x(j).toFixed(1)},${y(data[j].nav).toFixed(1)}`).join('')
        const area = `${line}L${x(i - 1).toFixed(1)},${M.top + ih}L${x(start).toFixed(1)},${M.top + ih}Z`
        segments.push({ line, area })
        start = i
      }
    }
    const xTickCount = width < 480 ? 3 : 5
    const xTicks = Array.from({ length: xTickCount }, (_, k) => Math.round((k / (xTickCount - 1)) * (data.length - 1)))
    return { t, x, y, ticks, segments, xTicks, ih }
  }, [data, width])

  const nearest = (px: number) => {
    if (!geo) return null
    let best = 0
    for (let i = 1; i < data.length; i++) if (Math.abs(geo.x(i) - px) < Math.abs(geo.x(best) - px)) best = i
    return best
  }

  const onMove = (e: PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    setHover(nearest(((e.clientX - r.left) / r.width) * width))
  }

  const onKey = (e: KeyboardEvent) => {
    if (!data.length) return
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault()
      const d = e.key === 'ArrowLeft' ? -1 : 1
      setHover((h) => Math.min(data.length - 1, Math.max(0, (h ?? data.length - 1) + d)))
    } else if (e.key === 'Escape') setHover(null)
  }

  const last = data[data.length - 1]
  const hp = hover !== null ? data[hover] : null

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div role="radiogroup" aria-label="Time range" className="inline-flex rounded-md border border-line p-0.5">
          {RANGES.map((r) => (
            <button
              key={r.key}
              role="radio"
              aria-checked={range === r.key}
              onClick={() => setRange(r.key)}
              className={`rounded px-3 py-1 text-xs font-semibold ${range === r.key ? 'bg-accent-soft text-ink' : 'text-muted hover:text-ink'}`}
            >
              {r.key}
            </button>
          ))}
        </div>
        <button type="button" className="ml-auto text-xs font-medium text-muted hover:text-ink" onClick={() => setShowTable((s) => !s)} aria-pressed={showTable}>
          {showTable ? 'View as chart' : 'View as table'}
        </button>
      </div>

      <div ref={wrapRef} className="relative">
        {showTable ? (
          <div className="max-h-[260px] overflow-y-auto rounded-md border border-line">
            <table className="w-full text-sm">
              <caption className="sr-only">Fund NAV per unit by date</caption>
              <thead className="sticky top-0 bg-surface text-left text-xs text-muted">
                <tr><th className="px-3 py-2 font-medium">Date</th><th className="px-3 py-2 text-right font-medium">NAV</th></tr>
              </thead>
              <tbody className="divide-y divide-line font-mono">
                {[...data].reverse().map((p) => (
                  <tr key={p.date + p.generation}><td className="px-3 py-1.5">{fmtDate(p.date)}</td><td className="px-3 py-1.5 text-right">{fmtNum(p.nav)}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : !geo ? (
          <p className="py-16 text-center text-sm text-muted">Not enough NAV history to chart yet.</p>
        ) : (
          <>
            <svg
              width={width}
              height={H}
              viewBox={`0 0 ${width} ${H}`}
              className="block touch-none select-none outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
              role="img"
              tabIndex={0}
              aria-label={`Fund NAV per unit, ${fmtDate(data[0].date)} to ${fmtDate(last.date)}, latest ${fmtNum(last.nav)}. Use arrow keys to read values.`}
              onPointerMove={onMove}
              onPointerDown={onMove}
              onPointerLeave={() => setHover(null)}
              onKeyDown={onKey}
              onBlur={() => setHover(null)}
            >
              <defs>
                <linearGradient id="navFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="rgb(var(--chart))" stopOpacity="0.14" />
                  <stop offset="100%" stopColor="rgb(var(--chart))" stopOpacity="0" />
                </linearGradient>
              </defs>
              {geo.ticks.map((v) => (
                <g key={v}>
                  <line x1={M.left} x2={width - M.right} y1={geo.y(v)} y2={geo.y(v)} stroke="rgb(var(--line))" strokeWidth={1} />
                  <text x={M.left - 10} y={geo.y(v)} dy="0.32em" textAnchor="end" className="fill-muted font-mono text-[10.5px]">{fmtNum(v, v % 1 ? 1 : 0)}</text>
                </g>
              ))}
              {geo.xTicks.map((i, k) => (
                <text key={i} x={geo.x(i)} y={H - 8} textAnchor={k === 0 ? 'start' : k === geo.xTicks.length - 1 ? 'end' : 'middle'} className="fill-muted font-mono text-[10.5px]">
                  {fmtDate(data[i].date, { month: 'short', year: '2-digit' })}
                </text>
              ))}
              {geo.segments.map((s, k) => (
                <g key={k}>
                  <path d={s.area} fill="url(#navFill)" />
                  <path d={s.line} fill="none" stroke="rgb(var(--chart))" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                </g>
              ))}
              <circle cx={geo.x(data.length - 1)} cy={geo.y(last.nav)} r={4} fill="rgb(var(--chart))" stroke="rgb(var(--surface))" strokeWidth={2} />
              {hp && hover !== null && (
                <g pointerEvents="none">
                  <line x1={geo.x(hover)} x2={geo.x(hover)} y1={M.top} y2={M.top + geo.ih} stroke="rgb(var(--muted))" strokeOpacity={0.5} strokeWidth={1} />
                  <circle cx={geo.x(hover)} cy={geo.y(hp.nav)} r={5} fill="rgb(var(--chart))" stroke="rgb(var(--surface))" strokeWidth={2} />
                </g>
              )}
            </svg>
            {hp && hover !== null && (
              <div
                role="status"
                className="pointer-events-none absolute top-1 z-10 rounded-md border border-line bg-surface px-3 py-2 shadow-sm"
                style={{ left: Math.min(Math.max(geo.x(hover) - 60, 0), width - 130) }}
              >
                <div className="font-mono text-sm font-semibold text-ink">{fmtNum(hp.nav)}</div>
                <div className="text-[11px] text-muted">{fmtDate(hp.date)}</div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
