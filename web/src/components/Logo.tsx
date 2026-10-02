import { site } from '../site.config'

const MARK =
  'M229.592 92.2116C232.959 93.5674 232.925 98.3461 229.538 99.6536L99.6326 149.815C95.9576 151.234 92.6606 147.046 94.903 143.807L110.942 120.639C112.374 118.57 111.564 115.709 109.26 114.699L74.1763 99.3083C71.0127 97.9205 70.9777 93.4449 74.1193 92.0078L109.156 75.9805C111.392 74.9577 112.185 72.1788 110.825 70.1305L94.6287 45.7365C92.4555 42.4633 95.8105 38.346 99.4551 39.8135L229.592 92.2116Z'

/** FrontierTradeLight's mark (from the main project's favicon) + wordmark. */
export default function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true" className="flex-shrink-0">
        <rect width="64" height="64" rx="14" className="fill-accent" />
        <path transform="translate(10,16.25) scale(0.2544) translate(-65,-33)" d={MARK} className="fill-accent-ink" />
      </svg>
      {!compact && <span className="text-[15px] font-extrabold tracking-tight">{site.name}</span>}
    </span>
  )
}
