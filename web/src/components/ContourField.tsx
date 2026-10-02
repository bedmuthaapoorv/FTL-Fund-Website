/**
 * Abstract contour-line artwork. Deterministic (no randomness) so the
 * statically rendered HTML matches what the client hydrates.
 */
function ring(cx: number, cy: number, r: number, k: number) {
  const pts: string[] = []
  const n = 96
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * Math.PI * 2
    const wobble =
      1 + 0.09 * Math.sin(3 * t + k * 0.55) + 0.05 * Math.sin(5 * t - k * 0.3) + 0.025 * Math.sin(9 * t + k)
    const x = cx + r * wobble * Math.cos(t) * 1.25
    const y = cy + r * wobble * Math.sin(t)
    pts.push(`${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`)
  }
  return pts.join('') + 'Z'
}

export default function ContourField({ className = '' }: { className?: string }) {
  const rings = Array.from({ length: 16 }, (_, k) => ring(300, 300, 26 + k * 17, k))
  return (
    <svg viewBox="0 0 600 600" className={className} aria-hidden="true" fill="none">
      {rings.map((d, k) => (
        <path key={k} d={d} stroke="currentColor" strokeWidth={k % 4 === 0 ? 1.1 : 0.7} opacity={0.18 + (k % 4 === 0 ? 0.35 : 0) - k * 0.006} />
      ))}
      <circle cx="300" cy="300" r="3" fill="currentColor" opacity="0.7" />
    </svg>
  )
}
