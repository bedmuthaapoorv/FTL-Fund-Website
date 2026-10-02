import os
import tempfile
import time
from datetime import date

# Configure before the app is imported. All data in tests is fake.
_tmp = tempfile.mkdtemp()
os.environ.update(
    ENV="test",
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    DATA_ENCRYPTION_KEY="Wm9nUHV0TndHWjN2a3VxWlF4c2V0Ym9yZ0tUYmJ6Zk0=",  # test-only key
    SYNC_SECRET="test-sync-secret",
    LOGIN_RATE_LIMIT="1000/minute",
    CONTACT_RATE_LIMIT="1000/minute",
    EMAIL_BACKEND="console",
)

import pyotp  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CapitalEvent, FundState, NavPoint, User  # noqa: E402
from app.ratelimit import limiter  # noqa: E402
from app.security import encrypt_secret, hash_password  # noqa: E402

PASSWORD = "correct-horse-battery"  # test-only


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limiter.reset()
    yield


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def client() -> TestClient:
    return TestClient(app, headers={"X-FTH-CSRF": "1"})


@pytest.fixture
def anon():
    return client()


def make_user(email: str, role: str = "investor", investor_id: str | None = None, status: str = "active") -> tuple[int, str]:
    secret = pyotp.random_base32()
    with SessionLocal() as s:
        u = User(
            email=email, role=role, status=status, investor_id=investor_id,
            password_hash=hash_password(PASSWORD), totp_secret_enc=encrypt_secret(secret), mfa_enabled=True,
        )
        s.add(u)
        s.commit()
        return u.id, secret


def next_code(user_id: int, secret: str) -> str:
    """A TOTP code the server will accept: newer than the last used step."""
    with SessionLocal() as s:
        last = s.get(User, user_id).last_totp_step
    t = pyotp.TOTP(secret)
    now_step = int(time.time()) // t.interval
    step = max(now_step - 1, last + 1)
    assert step <= now_step + 1, "ran out of usable TOTP steps in this window"
    return t.at(step * t.interval)


def login(email: str, user_id: int, secret: str) -> TestClient:
    c = client()
    r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200 and r.json()["next"] == "mfa", r.text
    r = c.post("/api/auth/mfa/verify", json={"code": next_code(user_id, secret)})
    assert r.status_code == 200, r.text
    return c


def seed_fund():
    """Two investors (A, B) with distinct, fake capital events."""
    with SessionLocal() as s:
        s.add(FundState(id=1, current_generation=1))
        s.add_all([
            NavPoint(date=date(2026, 1, 1), nav=100.0, generation=1),
            NavPoint(date=date(2026, 6, 1), nav=110.0, generation=1),
            NavPoint(date=date(2026, 9, 1), nav=120.0, generation=1),
        ])
        s.add_all([
            CapitalEvent(investor_id="INV-A", date=date(2026, 1, 1), type="DEPOSIT", amount=100000, nav=100, units=1000, seq=0),
            CapitalEvent(investor_id="INV-B", date=date(2026, 1, 1), type="DEPOSIT", amount=500000, nav=100, units=5000, seq=1),
            CapitalEvent(investor_id="INV-B", date=date(2026, 6, 1), type="WITHDRAWAL", amount=110000, nav=110, units=-1000, seq=2),
        ])
        s.commit()


@pytest.fixture
def two_investors():
    seed_fund()
    a_id, a_secret = make_user("a@example.test", investor_id="INV-A")
    b_id, b_secret = make_user("b@example.test", investor_id="INV-B")
    return {
        "a": login("a@example.test", a_id, a_secret),
        "b": login("b@example.test", b_id, b_secret),
    }
