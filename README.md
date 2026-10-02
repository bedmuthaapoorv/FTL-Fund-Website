# Frontier TradeLight website

Public website and investor portal for the Frontier TradeLight fund.

- **Public site.** Home, Approach (behind an eligibility click-through), Insights, Contact, and legal pages. It carries no performance data and does not solicit investment.
- **Investor portal.** Invite-only, with password and TOTP two-step verification. Each investor sees only their own position, contribution history, and the fund's NAV chart.
- **Admin area.** Invite investors, link accounts to synced data, reset access, view sync history, and read the audit log.
- **Sync.** A read-only script on the fund manager's machine pushes a signed, pseudonymised snapshot from FrontierTradeLight's Fund Manager. The website never connects back.

> **Legal copy is draft.** All disclaimers, risk warnings, the privacy policy, terms, and eligibility wording are placeholders until securities counsel reviews them. See [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md).

## Layout

```
web/    Vite + React + TypeScript + Tailwind. Public routes are prerendered (vite-react-ssg)
  src/site.config.ts      name, official channels, interstitial on/off + labels, feature flags
  src/content/            Markdown: legal/*.md, insights/*.md, interstitial.md
api/    FastAPI + SQLAlchemy + Alembic. Auth, portal API, admin API, sync endpoint
sync/   export_snapshot.py: stdlib-only exporter run on the FrontierTradeLight machine
```

Unconfirmed facts are written as `[PLACEHOLDER: ...]` and render highlighted. Search for `PLACEHOLDER` and `TODO(counsel)` to find them all.

## Local development

Requires Python 3.12+ and Node 18+.

**Quick start (macOS):** double-click `Start Website.command`. On first run it sets up everything it needs: the Python environment, dependencies, an `api/.env` with fresh local secrets, database migrations, and npm packages. It then starts the API (port 8100) and the site (port 5180) and opens your browser. Closing the window or pressing Ctrl+C stops both servers.

Manual steps:

```bash
# API
cd api
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env        # then fill DATA_ENCRYPTION_KEY and SYNC_SECRET (commands are in the file)
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed          # FAKE investors + data (dev only)
.venv/bin/uvicorn app.main:app --port 8100 --reload

# Web (second terminal)
cd web
npm install
npm run dev                  # http://localhost:5180, proxies /api to :8100
```

The seeded dev accounts use the password and TOTP secrets in `api/app/seed.py`. Add those secrets to any authenticator app, or generate a code with `pyotp`. All seeded people and amounts are fictional.

Contact-form messages print to the API console locally (`EMAIL_BACKEND=console`).

### Tests

```bash
cd api && .venv/bin/pytest          # auth, MFA, isolation, sync, admin, hardening
cd web && npm run typecheck
```

`tests/test_isolation.py` proves that one investor cannot read another's data by changing IDs in paths, query strings, headers, or cookies. It also checks that every non-public route rejects anonymous requests.

## Accounts

There is no public sign-up.

1. **Create the admin.** Run `.venv/bin/python -m app.cli create-admin you@yourdomain`. It prints a one-time invite link, valid for 72 hours. Open the link, set a password, and scan the QR code.
2. **Invite investors.** In **Admin → Investors**, create an invitation, then send the link from the official email address. The investor sets a password, enrols TOTP, and receives 10 one-time recovery codes.
3. **Lost device or suspected compromise.** Use **Reset access**. It revokes the password, MFA and sessions, and creates a fresh invite.
4. **Admin locked out.** Run `python -m app.cli invite you@yourdomain`.

A password alone can never enrol an authenticator. Enrolment is reachable only through an invite link.

## Syncing from FrontierTradeLight

The source of truth stays in FrontierTradeLight. The script is one-way and read-only.

| Reads | Never opens |
|---|---|
| `nav_history.csv` (Date, NAV, Generation)<br>`capital_events.csv`<br>`generation.json` | `investors.csv` (names, emails)<br>`fund_holdings.csv`<br>`cash.json`<br>`documents/` |

FrontierTradeLight's `InvestorID` is a slug of the investor's name. The script therefore replaces each one with `inv_` + HMAC-SHA256(`SYNC_ID_PEPPER`, id). The pepper lives only in `sync/.env` on your machine, so the server cannot reverse the pseudonyms.

**Snapshot format (schema v1):**

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-02T05:00:00+00:00",
  "currency": "INR",
  "current_generation": 1,
  "nav_history": [{ "date": "2026-09-28", "nav": 104.21, "generation": 1 }],
  "investors": [
    { "investor_id": "inv_0123456789abcdef0123",
      "events": [{ "date": "2026-01-05", "type": "DEPOSIT", "amount": 300000, "nav": 100.0, "units": 3000.0 }] }
  ]
}
```

The server rejects any snapshot that has:
- unknown fields,
- raw (non-pseudonymised) IDs,
- units that don't equal amount ÷ NAV,
- a duplicate key.

A valid snapshot replaces all fund data in one transaction. Re-sending the same snapshot is harmless. Every run, accepted or rejected, appears in **Admin → Data sync**.

```bash
cd sync
cp .env.example .env               # set SYNC_URL, SYNC_SECRET (= server's), SYNC_ID_PEPPER (local only)
python3 export_snapshot.py         # dry run: prints a summary, writes out/snapshot.json
python3 export_snapshot.py --show-ids   # local InvestorID -> pseudonym map, for linking accounts
python3 export_snapshot.py --push  # HMAC-signed POST to /api/sync
```

Pushes are signed over `timestamp + body` and rejected if more than 5 minutes old. As an alternative, `out/snapshot.json` can be uploaded in **Admin → Data sync**.

Keep `SYNC_ID_PEPPER` stable. Changing it changes every pseudonym, and you would then need to re-link all accounts.

## Deployment

Hosting has not been chosen yet. The repo ships a single host-agnostic image: FastAPI serves both the API and the prerendered site from one origin.

```bash
docker build -t fth-website .
docker run -p 8000:8000 --env-file prod.env fth-website
```

Production refuses to boot unless all of these are true:

| Setting | Requirement |
|---|---|
| `SITE_URL` | uses `https://` |
| `DATA_ENCRYPTION_KEY` | is set |
| `SYNC_SECRET` | 32+ characters |
| `DATABASE_URL` | points at Postgres |
| Email | `EMAIL_BACKEND=smtp` with credentials |

Requirements for the host:

- **TLS.** Terminate it at the platform or proxy. The app sends HSTS in production.
- **Proxy address.** Set `FORWARDED_ALLOW_IPS` to the proxy's address so login rate limits see real client IPs.
- **Single instance.** Run one container. Rate limits are kept in memory.
- **Database.** Use a managed Postgres with automated daily backups and point-in-time recovery. Migrations run on start (`alembic upgrade head`).
- **Dependency audits.** Run `pip-audit -r api/requirements.txt` and `npm audit` before each deploy.

### Security baseline

**Credentials and sessions**
- Argon2id password hashing.
- TOTP with replay protection and one-time recovery codes. TOTP secrets are encrypted at rest with Fernet.
- Server-side sessions with hashed tokens, `HttpOnly`, `Secure`, and `SameSite=Strict` cookies. Sessions rotate whenever privilege changes.
- A CSRF header is required on every state-changing request.

**Abuse limits**
- Logins are rate-limited per IP.
- Accounts lock after 5 failed attempts.

**Headers and content**
- Strict CSP with no `unsafe-inline` scripts. The few inline hydration scripts are allowed by build-time hashes (`web/scripts/csp-hashes.mjs`).
- HSTS, `nosniff`, `frame-ancestors 'none'`, and `no-store` on every API response.
- Fonts are self-hosted, so the site makes no third-party requests.

**Records and secrets**
- Every admin action, sync, and sign-in event is written to the audit log.
- No secrets live in the repo: only `.env.example` files are committed.

## Deferred (by decision)

- Documents vault and investor letters. The design leaves room for them. Per-document access checks, signed expiring download URLs, and a download access log must come with that feature.
- Team / About page. It is built but hidden; set `features.team` in `site.config.ts` to show it.
- Hosting choice and domain.
