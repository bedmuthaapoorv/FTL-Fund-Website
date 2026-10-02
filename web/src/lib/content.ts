import { site } from '../site.config'

type Frontmatter = Record<string, string>
export type Doc = { slug: string; meta: Frontmatter; body: string }

// Markdown content is bundled at build time; nothing is fetched at runtime.
const legalFiles = import.meta.glob('../content/legal/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
const insightFiles = import.meta.glob('../content/insights/*.md', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
import interstitialRaw from '../content/interstitial.md?raw'

const slugOf = (path: string) => path.split('/').pop()!.replace(/\.md$/, '')

function parse(raw: string): { meta: Frontmatter; body: string } {
  const meta: Frontmatter = {}
  let body = raw
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?/)
  if (m) {
    for (const line of m[1].split('\n')) {
      const i = line.indexOf(':')
      if (i > 0) meta[line.slice(0, i).trim()] = line.slice(i + 1).trim()
    }
    body = raw.slice(m[0].length)
  }
  // Authoring notes (TODO(counsel) etc.) live in HTML comments; never render them.
  body = body.replace(/<!--[\s\S]*?-->/g, '').trim()
  body = body
    .replaceAll('{{officialDomain}}', site.officialDomain ?? '[PLACEHOLDER: official domain, not yet registered]')
    .replaceAll('{{officialEmail}}', site.officialEmail)
  return { meta, body }
}

export const legalDocs: Doc[] = Object.entries(legalFiles).map(([p, raw]) => ({ slug: slugOf(p), ...parse(raw) }))
export const legalOrder = ['disclaimer', 'risk', 'privacy', 'terms', 'impersonation']
export const getLegal = (slug: string) => legalDocs.find((d) => d.slug === slug)

export const insights: Doc[] = Object.entries(insightFiles)
  .map(([p, raw]) => ({ slug: slugOf(p), ...parse(raw) }))
  .sort((a, b) => b.meta.date.localeCompare(a.meta.date))
export const getInsight = (slug: string) => insights.find((d) => d.slug === slug)

export const interstitial = parse(interstitialRaw).body

export function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
}
