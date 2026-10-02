from sqlalchemy import select

from app.models import AuditLog, User

from .conftest import PASSWORD, SessionLocal, client, login, make_user, seed_fund


def admin_client():
    uid, secret = make_user("admin@example.test", role="admin")
    return login("admin@example.test", uid, secret)


def actions() -> list[str]:
    with SessionLocal() as s:
        return [a.action for a in s.scalars(select(AuditLog).order_by(AuditLog.id))]


def test_create_investor_and_invite_link_works():
    admin = admin_client()
    r = admin.post("/api/admin/users", json={"email": "New@Example.com", "display_name": "Fake New", "investor_id": "INV-A"})
    assert r.status_code == 200
    token = r.json()["invite_link"].split("#token=")[1]
    assert client().post("/api/auth/invite/check", json={"token": token}).json()["email"] == "new@example.com"
    assert admin.post("/api/admin/users", json={"email": "new@example.com"}).status_code == 409
    assert "admin.user_created" in actions()


def test_investor_id_cannot_be_linked_twice():
    admin = admin_client()
    admin.post("/api/admin/users", json={"email": "a@example.com", "investor_id": "INV-A"})
    assert admin.post("/api/admin/users", json={"email": "b@example.com", "investor_id": "INV-A"}).status_code == 409


def test_link_unlink_and_audit_records_change():
    seed_fund()
    admin = admin_client()
    uid = admin.post("/api/admin/users", json={"email": "a@example.com"}).json()["user"]["id"]
    assert admin.patch(f"/api/admin/users/{uid}", json={"investor_id": "INV-A"}).json()["investor_id"] == "INV-A"
    assert admin.patch(f"/api/admin/users/{uid}", json={"unlink": True}).json()["investor_id"] is None
    with SessionLocal() as s:
        log = s.scalars(select(AuditLog).where(AuditLog.action == "admin.user_updated")).all()
    assert log[0].detail["changes"]["investor_id"] == [None, "INV-A"]
    ids = {r["investor_id"]: r for r in admin.get("/api/admin/investor-ids").json()}
    assert set(ids) == {"INV-A", "INV-B"} and ids["INV-A"]["linked_to"] is None


def test_disable_ends_sessions_and_reset_access_revokes_credentials():
    admin = admin_client()
    uid, secret = make_user("a@example.com", investor_id="INV-A")
    inv = login("a@example.com", uid, secret)
    assert admin.patch(f"/api/admin/users/{uid}", json={"status": "disabled"}).status_code == 200
    assert inv.get("/api/me/summary").status_code == 401

    r = admin.post(f"/api/admin/users/{uid}/reset-access")
    assert r.status_code == 200 and "#token=" in r.json()["invite_link"]
    with SessionLocal() as s:
        u = s.get(User, uid)
        assert u.password_hash is None and not u.mfa_enabled and u.status == "invited"
    assert client().post("/api/auth/login", json={"email": "a@example.com", "password": PASSWORD}).status_code == 401
    assert {"admin.user_updated", "admin.access_reset"} <= set(actions())


def test_admin_cannot_lock_themselves_out():
    admin = admin_client()
    me = next(u for u in admin.get("/api/admin/users").json() if u["role"] == "admin")
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"status": "disabled"}).status_code == 400
    assert admin.post(f"/api/admin/users/{me['id']}/reset-access").status_code == 400


def test_investor_cannot_use_any_admin_write():
    uid, secret = make_user("a@example.com", investor_id="INV-A")
    inv = login("a@example.com", uid, secret)
    assert inv.post("/api/admin/users", json={"email": "x@example.com"}).status_code == 403
    assert inv.patch(f"/api/admin/users/{uid}", json={"investor_id": "INV-B"}).status_code == 403
    assert inv.post(f"/api/admin/users/{uid}/reset-access").status_code == 403
    assert inv.get("/api/admin/audit").status_code == 403


def test_audit_endpoint_lists_actions():
    admin = admin_client()
    admin.post("/api/admin/users", json={"email": "a@example.com"})
    entries = admin.get("/api/admin/audit").json()
    assert entries[0]["action"] == "admin.user_created" and entries[0]["actor"] == "admin@example.test"
