import { site } from '../site.config'

/** Visible on every legal page until counsel has reviewed the copy. */
export default function DraftBanner({ className = '' }: { className?: string }) {
  if (site.legalReviewedByCounsel) return null
  return (
    <div role="note" className={`rounded-lg border border-warn/30 bg-warn-soft px-4 py-3 text-sm text-warn ${className}`}>
      <strong className="font-semibold">Draft — TODO:</strong> this legal wording is a placeholder and must be reviewed by
      securities counsel before publication. It is not final.
    </div>
  )
}
