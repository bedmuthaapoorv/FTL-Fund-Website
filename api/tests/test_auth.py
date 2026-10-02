from datetime import timedelta

import pyotp
from sqlalchemy import select

from app.accounts import issue_invite
from app.models import AuditLog, Invite, User, utcnow

from .conftest import PASSWORD, SessionLocal, client, login, make_user, next_code


def invite(email: str, role: str = "investor", investor_id: str | None = None) -> str:
    with SessionLocal() as s:
        u = User(email=email, role=role, status="invited", investor_id=investor_id)
        s.add(u)
        s.flush()
        link = issue_invite(s, u)
        s.commit()
    return link.split("#token=")[1]


def test_full_invite_enrolment_flow():
    token = invite("new@example.test")
    c = client()
    assert c.post("/api/auth/invite/check", json={"token": token}).json() == {"email": "new@example.test"}
    r = c.post("/api/auth/invite/accept", json={"token": token, "password": PASSWORD})
    assert r.json() == {"next": "enroll"}
    assert c.get("/api/auth/me").json()["stage"] == "enroll"
    assert c.get("/api/me/summary").status_code == 401  # not usable until MFA is set up

    setup = c.get("/api/auth/mfa/setup").json()
    assert setup["uri"].startswith("otpauth://totp/") and "<svg" in setup["qr_svg"]
    r = c.post("/api/auth/mfa/enroll", json={"code": pyotp.TOTP(setup["secret"]).now()})
    assert r.status_code == 200
    assert len(r.json()["recovery_codes"]) == 10
    assert c.get("/api/auth/me").json()["stage"] == "full"
    assert c.get("/api/me/summary").status_code == 200


def test_invite_is_single_use_and_expires():
    token = invite("x@example.test")
    assert client().post("/api/auth/invite/accept", json={"token": token, "password": PASSWORD}).status_code == 200
    assert client().post("/api/auth/invite/accept", json={"token": token, "password": PASSWORD}).status_code == 400

    token2 = invite("y@example.test")
    with SessionLocal() as s:
        for inv in s.scalars(select(Invite)):
            inv.expires_at = utcnow() - timedelta(minutes=1)
        s.commit()
    assert client().post("/api/auth/invite/accept", json={"token": token2, "password": PASSWORD}).status_code == 400


def test_reissuing_invite_invalidates_previous_link():
    old = invite("z@example.test")
    with SessionLocal() as s:
        issue_invite(s, s.scalar(select(User).where(User.email == "z@example.test")))
        s.commit()
    assert client().post("/api/auth/invite/accept", json={"token": old, "password": PASSWORD}).status_code == 400


def test_weak_password_rejected():
    token = invite("w@example.test")
    r = client().post("/api/auth/invite/accept", json={"token": token, "password": "short"})
    assert r.status_code == 400 and "12" in r.json()["detail"]


def test_bad_password_and_unknown_email_look_identical():
    make_user("a@example.test")
    r1 = client().post("/api/auth/login", json={"email": "a@example.test", "password": "wrong-password-x"})
    r2 = client().post("/api/auth/login", json={"email": "nobody@example.test", "password": "wrong-password-x"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_email_is_case_insensitive():
    uid, secret = make_user("a@example.test")
    c = client()
    assert c.post("/api/auth/login", json={"email": "A@Example.TEST", "password": PASSWORD}).status_code == 200


def test_wrong_mfa_code_rejected_and_lockout():
    uid, secret = make_user("a@example.test")
    for _ in range(5):
        c = client()
        c.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
        assert c.post("/api/auth/mfa/verify", json={"code": "000000"}).status_code == 401
    # Locked: even the right password is refused, with the generic message.
    r = client().post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
    assert r.status_code == 401
    with SessionLocal() as s:
        assert s.get(User, uid).locked_until is not None


def test_password_lockout():
    make_user("a@example.test")
    for _ in range(5):
        client().post("/api/auth/login", json={"email": "a@example.test", "password": "nope-nope-nope"})
    assert client().post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD}).status_code == 401


def test_totp_code_cannot_be_replayed():
    uid, secret = make_user("a@example.test")
    code = next_code(uid, secret)
    c1 = client()
    c1.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
    assert c1.post("/api/auth/mfa/verify", json={"code": code}).status_code == 200
    c2 = client()
    c2.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
    assert c2.post("/api/auth/mfa/verify", json={"code": code}).status_code == 401


def test_recovery_code_works_once():
    token = invite("r@example.test")
    c = client()
    c.post("/api/auth/invite/accept", json={"token": token, "password": PASSWORD})
    secret = c.get("/api/auth/mfa/setup").json()["secret"]
    codes = c.post("/api/auth/mfa/enroll", json={"code": pyotp.TOTP(secret).now()}).json()["recovery_codes"]

    for expected in (200, 401):
        c2 = client()
        c2.post("/api/auth/login", json={"email": "r@example.test", "password": PASSWORD})
        assert c2.post("/api/auth/mfa/verify", json={"recovery_code": codes[0].lower()}).status_code == expected


def test_csrf_header_required_for_writes():
    make_user("a@example.test")
    from fastapi.testclient import TestClient
    from app.main import app
    bare = TestClient(app)
    assert bare.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD}).status_code == 403
    assert bare.post("/api/contact", json={}).status_code == 403


def test_logout_kills_session():
    uid, secret = make_user("a@example.test", investor_id="INV-A")
    c = login("a@example.test", uid, secret)
    token = c.cookies.get("fth_session")
    assert c.post("/api/auth/logout").status_code == 200
    replay = client()
    replay.cookies.set("fth_session", token)
    assert replay.get("/api/me/summary").status_code == 401


def test_disabled_user_loses_access():
    uid, secret = make_user("a@example.test", investor_id="INV-A")
    c = login("a@example.test", uid, secret)
    with SessionLocal() as s:
        s.get(User, uid).status = "disabled"
        s.commit()
    assert c.get("/api/me/summary").status_code == 401
    assert client().post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD}).status_code == 401


def test_session_cookie_flags():
    uid, secret = make_user("a@example.test")
    c = client()
    r = c.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie


def test_session_rotates_after_mfa():
    uid, secret = make_user("a@example.test")
    c = client()
    c.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD})
    pre = c.cookies.get("fth_session")
    c.post("/api/auth/mfa/verify", json={"code": next_code(uid, secret)})
    assert c.cookies.get("fth_session") != pre
    stale = client()
    stale.cookies.set("fth_session", pre)
    assert stale.get("/api/auth/me").status_code == 401


def test_security_events_are_audited():
    uid, secret = make_user("a@example.test")
    client().post("/api/auth/login", json={"email": "a@example.test", "password": "wrong-password-x"})
    login("a@example.test", uid, secret)
    with SessionLocal() as s:
        actions = [a.action for a in s.scalars(select(AuditLog))]
    assert "auth.login_failed" in actions and "auth.login" in actions
