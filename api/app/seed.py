"""DEV ONLY: fake investors and fund data for local development.
Every name, email and amount here is invented. Real data only ever arrives
at runtime through the FrontierTradeLight sync."""

import random
import sys
from datetime import date, timedelta

from sqlalchemy import delete

from .config import get_settings
from .db import SessionLocal
from .models import AuditLog, CapitalEvent, FundState, Invite, NavPoint, RecoveryCode, Session, SyncRun, User, utcnow
from .security import encrypt_secret, hash_password

# Dev-only credentials for the seeded accounts. Never used outside ENV=dev.
DEV_PASSWORD = "dev-only-password-1"
DEV_TOTP_SECRETS = {
    "admin@example.test": "JBSWY3DPEHPK3PXPADMIN234",
    "asha@example.test": "JBSWY3DPEHPK3PXPASHA2345",
    "vikram@example.test": "JBSWY3DPEHPK3PXPVIKRAM23",
    "meera@example.test": "JBSWY3DPEHPK3PXPMEERA234",
    "unlinked@example.test": "JBSWY3DPEHPK3PXPUNLINKED",
}

USERS = [
    ("admin@example.test", "Fund Admin (fake)", "admin", None),
    ("asha@example.test", "Asha Rao (fake)", "investor", "INV-001"),
    ("vikram@example.test", "Vikram Shah (fake)", "investor", "INV-002"),
    ("meera@example.test", "Meera Iyer (fake)", "investor", "INV-003"),
    ("unlinked@example.test", "Not Yet Linked (fake)", "investor", None),
]

# (investor_id, date, type, amount INR)
EVENTS = [
    ("INV-001", date(2025, 4, 7), "DEPOSIT", 500000),
    ("INV-002", date(2025, 4, 7), "DEPOSIT", 1000000),
    ("INV-001", date(2025, 10, 6), "DEPOSIT", 200000),
    ("INV-003", date(2026, 1, 5), "DEPOSIT", 300000),
    ("INV-002", date(2026, 3, 2), "WITHDRAWAL", 150000),
]


def _nav_series(start: date, end: date) -> dict[date, float]:
    rng = random.Random(7)
    nav, d, out = 100.0, start, {}
    while d <= end:
        out[d] = round(nav, 4)
        nav *= 1 + rng.gauss(0.0022, 0.016)
        d += timedelta(days=7)
    return out


def seed() -> None:
    if get_settings().env != "dev":
        sys.exit("Refusing to seed: ENV is not 'dev'.")
    with SessionLocal() as db:
        for model in (CapitalEvent, NavPoint, FundState, RecoveryCode, Session, Invite, AuditLog, SyncRun, User):
            db.execute(delete(model))

        navs = _nav_series(date(2025, 4, 7), date(2026, 9, 28))
        db.add(FundState(id=1, current_generation=1, as_of=utcnow()))
        db.add_all(NavPoint(date=d, nav=v, generation=1) for d, v in navs.items())
        for seq, (inv, d, typ, amount) in enumerate(EVENTS):
            nav = navs[d]
            units = amount / nav if typ == "DEPOSIT" else -(amount / nav)
            db.add(CapitalEvent(investor_id=inv, date=d, type=typ, amount=amount, nav=nav, units=units, seq=seq))

        for email, name, role, inv in USERS:
            db.add(User(
                email=email, display_name=name, role=role, status="active", investor_id=inv,
                password_hash=hash_password(DEV_PASSWORD),
                totp_secret_enc=encrypt_secret(DEV_TOTP_SECRETS[email]), mfa_enabled=True,
            ))
        db.commit()
    print(f"Seeded {len(USERS)} fake users, {len(navs)} NAV points, {len(EVENTS)} capital events.")
    print("Dev logins: see DEV_PASSWORD / DEV_TOTP_SECRETS in app/seed.py")
