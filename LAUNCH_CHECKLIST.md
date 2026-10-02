# Launch checklist

Nothing here is optional. Tick each item with the date and the person who confirmed it.

## Legal and compliance (blocking)

- [ ] **Legal structure and regime decided.** Choose between SEBI AIF (Category III?), PMS, or other, and record which rules govern marketing and investor eligibility.
- [ ] **Counsel has reviewed the eligibility of the target audience.** The current plan is Indian residents, open to anyone, with a ₹50k minimum. AIF and PMS minimums are much higher (₹1 crore and ₹50 lakh), and pooled money from the public may fall under collective-investment-scheme rules. Until counsel confirms, the minimum ticket appears nowhere on the site.
- [ ] **Counsel has reviewed ALL legal copy and approved the final wording:**
  - [ ] `web/src/content/legal/disclaimer.md`
  - [ ] `web/src/content/legal/risk.md`
  - [ ] `web/src/content/legal/privacy.md` (including DPDP Act 2023 obligations and the grievance officer)
  - [ ] `web/src/content/legal/terms.md`
  - [ ] `web/src/content/legal/impersonation.md`
  - [ ] `web/src/content/interstitial.md` and the accept/decline labels in `site.config.ts`
  - [ ] Footer notice (`web/src/components/Footer.tsx`)
  - [ ] Portal disclaimer (`web/src/components/PortalLayout.tsx`) and the dashboard footnote (`web/src/portal/Overview.tsx`)
  - [ ] The article disclaimer at the end of each Insights essay
- [ ] **Counsel confirms the interstitial setting.** Decide whether it should be on and which pages it protects (`site.config.ts → interstitial`).
- [ ] **Counsel confirms the public copy.** Check that Home, Approach and the Insights essays contain no solicitation or performance claims.
- [ ] **Counsel has seen and approved the investor-facing figures.** This covers the per-investor return definition: gain on net capital contributed, not annualised.
- [ ] **Hypothetical and backtested performance stays off.** Confirm `features.showHypotheticalPerformance` is still `false`.
- [ ] **Counsel sign-off is recorded.** Once all of the above is done, set `legalReviewedByCounsel: true` in `site.config.ts`. This removes the draft banners.

## Content

- [ ] Every `[PLACEHOLDER: …]` is resolved or deliberately kept. To find them: `grep -rn PLACEHOLDER web/src`.
  - [ ] Legal entity name and registration details
  - [ ] Legal structure (Home hero)
  - [ ] Broker, custodian/DP, administrator, auditor and counsel (Approach)
  - [ ] Fees/expenses basis of NAV (dashboard)
- [ ] Domain registered. Set `officialDomain` in `site.config.ts`, and move the official email to that domain. A Gmail address is easy to impersonate.
- [ ] Team/About page written; set `features.team: true`.
- [ ] Insights drafts reviewed. Remove `draft: true` only after counsel has seen them.

## Security

- [ ] Production `.env` created on the host with fresh secrets: `DATA_ENCRYPTION_KEY` and `SYNC_SECRET`. Never reuse dev values.
- [ ] `SYNC_ID_PEPPER` generated and stored only on the FrontierTradeLight machine, with a backup in your password manager.
- [ ] HTTPS everywhere. Check that HSTS appears on responses.
- [ ] Headers checked on the live site with securityheaders.com or `curl -I`: CSP, HSTS, `X-Frame-Options`, `nosniff`.
- [ ] `FORWARDED_ALLOW_IPS` set to the proxy address. Confirm the audit log shows real client IPs.
- [ ] `pip-audit -r api/requirements.txt` is clean.
- [ ] `npm audit` reviewed. **Known accepted risk:** two moderate React Router v6 advisories, an open redirect via `<Link>`/`navigate` and SSR hydration deserialisation.
  - **Why accepted:** they are not exploitable here. Every navigation target is a constant or our own bundled content, and hydration data is our own static build output.
  - **Why not fixed:** fixes exist only in React Router v7, which `vite-react-ssg` does not support.
  - **Follow-up:** migrate to React Router v7 framework-mode prerendering.
- [ ] Admin account created via the CLI, with TOTP enrolled and recovery codes stored offline.
- [ ] Dev seed **not** run against production. It refuses unless `ENV=dev`.
- [ ] Test suite passes: `cd api && .venv/bin/pytest`.

## Operations

- [ ] Managed Postgres with automated daily backups and point-in-time recovery. Restore tested once.
- [ ] SMTP working: send a test contact-form message. For Gmail, use an App Password.
- [ ] First real sync:
  1. Dry run, then review the summary.
  2. Run `--push`.
  3. Link each investor account using `--show-ids`.
  4. Each investor confirms their figures match their statement.
- [ ] Uptime check on `/api/health`.
- [ ] Decide how often to sync, and who does it.

## Before launching the documents vault (deferred feature)

- [ ] Per-document visibility: fund-wide or for a single investor, enforced server-side, with isolation tests.
- [ ] Downloads only through signed, expiring URLs, with every download recorded in an access log.
