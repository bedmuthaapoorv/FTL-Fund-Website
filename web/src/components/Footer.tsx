import { Link } from 'react-router-dom'
import { site } from '../site.config'
import { getLegal, legalOrder } from '../lib/content'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="container-page grid gap-10 py-12 md:grid-cols-[1.2fr_2fr]">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-xs text-sm text-muted">
            Contact: <a className="link" href={`mailto:${site.officialEmail}`}>{site.officialEmail}</a>
          </p>
        </div>

        <div className="space-y-5 text-[13px] leading-relaxed text-muted">
          {!site.legalReviewedByCounsel && (
            <p className="font-mono text-[11px] uppercase tracking-wider text-warn">
              Draft legal notices — TODO: pending review by securities counsel
            </p>
          )}
          <p>
            Nothing on this website is an offer to sell, or a solicitation of an offer to buy, any security or investment
            product. Past performance is not indicative of future results. This website does not publish performance
            information.
          </p>
          <p>
            <strong className="font-semibold text-ink">Beware of impersonation.</strong> {site.name} communicates only
            via{' '}
            {site.officialDomain ? <>{site.officialDomain} and </> : <span className="placeholder-tag">[PLACEHOLDER: official domain]</span>}{' '}
            {site.officialEmail}. We never offer investments through social media or messaging groups, and never ask
            for payment to personal accounts.{' '}
            <Link className="link" to="/legal/impersonation">Read more</Link>
          </p>
          <nav aria-label="Legal" className="flex flex-wrap gap-x-5 gap-y-2 pt-1">
            {legalOrder.map((slug) => (
              <Link key={slug} to={`/legal/${slug}`} className="text-muted hover:text-ink">
                {getLegal(slug)?.meta.title}
              </Link>
            ))}
          </nav>
          <p className="text-[12px]">© {new Date().getFullYear()} <span className="placeholder-tag">[PLACEHOLDER: legal entity name]</span></p>
        </div>
      </div>
    </footer>
  )
}
