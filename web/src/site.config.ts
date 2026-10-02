/**
 * Site-wide configuration. Everything compliance-sensitive is switchable
 * here so wording/behaviour can change without touching page code.
 *
 * TODO(counsel): every flag below that affects legal posture must be
 * confirmed by securities counsel before launch. See LAUNCH_CHECKLIST.md.
 */
export const site = {
  name: 'Frontier TradeLight',
  shortName: 'FTH',

  // Official channels, named in the anti-impersonation notice.
  // No domain has been registered yet; leave null until one is.
  officialDomain: null as string | null,
  officialEmail: 'bedmuthaapoorv@gmail.com',

  // While false, every legal page and the footer carry a visible
  // "draft, pending counsel review" banner. Flip only after review.
  legalReviewedByCounsel: false,

  // Eligibility click-through shown before any page that describes the
  // fund's offering or process. Wording lives in content/interstitial.md.
  interstitial: {
    enabled: true,
    protectedPaths: ['/approach'],
    acceptLabel: 'I confirm and wish to continue',
    declineLabel: 'Return to home page',
  },

  features: {
    // Team/About page is written but hidden until its content is ready.
    team: false,
    // Hypothetical or backtested performance must never be shown unless
    // counsel has approved the accompanying disclosures. Nothing reads
    // this as true today; it exists so the decision is explicit.
    showHypotheticalPerformance: false,
  },
} as const

export type NavItem = { label: string; to: string }

export const nav: NavItem[] = [
  { label: 'Approach', to: '/approach' },
  ...(site.features.team ? [{ label: 'Team', to: '/team' }] : []),
  { label: 'Insights', to: '/insights' },
  { label: 'Contact', to: '/contact' },
]
