// Post-build: collect SHA-256 hashes of every inline <script> in dist/*.html
// (vite-react-ssg injects small hydration snippets) so the server's CSP can
// allow exactly those and nothing else -- no 'unsafe-inline'.
import { createHash } from 'node:crypto'
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const DIST = new URL('../dist/', import.meta.url).pathname
const hashes = new Set()
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p)
    else if (p.endsWith('.html')) {
      for (const [, body] of readFileSync(p, 'utf8').matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)) {
        hashes.add(`'sha256-${createHash('sha256').update(body, 'utf8').digest('base64')}'`)
      }
    }
  }
}
walk(DIST)
writeFileSync(join(DIST, 'csp-hashes.json'), JSON.stringify([...hashes].sort(), null, 2))
console.log(`csp-hashes.json: ${hashes.size} inline script hash(es)`)
