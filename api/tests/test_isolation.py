"""Proves an investor can only ever see their own data, no matter what IDs
they put in the request."""

from fastapi.routing import APIRoute
from sqlalchemy import select

from app.main import app
from app.models import CapitalEvent

from .conftest import SessionLocal, login, make_user, seed_fund

PUBLIC = {"/api/health", "/api/contact", "/api/sync"}


def event_ids(investor_id: str) -> list[int]:
    with SessionLocal() as s:
        return list(s.scalars(select(CapitalEvent.id).where(CapitalEvent.investor_id == investor_id)))


def test_summary_reflects_only_own_events(two_investors):
    a = two_investors["a"].get("/api/me/summary").json()
    b = two_investors["b"].get("/api/me/summary").json()
    assert a["units"] == 1000 and a["total_deposited"] == 100000 and a["total_withdrawn"] == 0
    assert b["units"] == 4000 and b["total_deposited"] == 500000 and b["total_withdrawn"] == 110000


def test_event_list_contains_only_own_events(two_investors):
    a_events = two_investors["a"].get("/api/me/events").json()
    assert {e["id"] for e in a_events} == set(event_ids("INV-A"))
    assert not {e["id"] for e in a_events} & set(event_ids("INV-B"))


def test_cannot_fetch_other_investors_event_by_id(two_investors):
    a = two_investors["a"]
    for b_event in event_ids("INV-B"):
        r = a.get(f"/api/me/events/{b_event}")
        assert r.status_code == 404
        # Indistinguishable from an ID that doesn't exist at all.
        assert r.json() == a.get("/api/me/events/999999").json()
    assert a.get(f"/api/me/events/{event_ids('INV-A')[0]}").status_code == 200


def test_injected_investor_id_params_are_ignored(two_investors):
    a = two_investors["a"]
    own = a.get("/api/me/summary").json()
    for path in ("/api/me/summary?investor_id=INV-B", "/api/me/summary?investorId=INV-B&id=2"):
        assert a.get(path).json() == own
    events = a.get("/api/me/events?investor_id=INV-B").json()
    assert {e["id"] for e in events} == set(event_ids("INV-A"))


def test_injected_investor_id_header_and_cookie_ignored(two_investors):
    a = two_investors["a"]
    own = a.get("/api/me/summary").json()
    a.cookies.set("investor_id", "INV-B")
    r = a.get("/api/me/summary", headers={"X-Investor-Id": "INV-B"})
    assert r.json() == own


def test_investor_cannot_reach_admin_routes(two_investors):
    a = two_investors["a"]
    assert a.get("/api/admin/users").status_code == 403


def test_admin_is_not_an_investor(two_investors):
    uid, secret = make_user("admin@example.test", role="admin")
    admin = login("admin@example.test", uid, secret)
    assert admin.get("/api/me/summary").status_code == 403
    assert admin.get("/api/admin/users").status_code == 200


def test_unlinked_investor_sees_nothing():
    seed_fund()
    uid, secret = make_user("new@example.test", investor_id=None)
    c = login("new@example.test", uid, secret)
    s = c.get("/api/me/summary").json()
    assert s["linked"] is False and s["units"] == 0 and s["current_value"] == 0
    assert c.get("/api/me/events").json() == []
    for eid in event_ids("INV-A") + event_ids("INV-B"):
        assert c.get(f"/api/me/events/{eid}").status_code == 404


def test_every_non_public_route_requires_auth(anon):
    """Guards against a future route that forgets its auth dependency."""
    seed_fund()
    checked = 0
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api") or route.path in PUBLIC:
            continue
        if route.path.startswith(("/api/auth/", "/api/docs", "/api/openapi")):
            continue
        path = route.path.replace("{event_id}", "1").replace("{user_id}", "1").replace("{doc_id}", "1")
        for method in route.methods - {"HEAD", "OPTIONS"}:
            r = anon.request(method, path, json={})
            assert r.status_code in (401, 403), f"{method} {route.path} -> {r.status_code}"
            checked += 1
    assert checked >= 4


def test_no_investor_route_takes_an_investor_id():
    """Investor-facing routes must derive scope from the session only."""
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith(("/api/me", "/api/fund")):
            names = {p.name.lower() for p in route.dependant.path_params + route.dependant.query_params}
            assert not any("investor" in n for n in names), route.path


def test_mfa_pending_session_cannot_read_data():
    seed_fund()
    make_user("a@example.test", investor_id="INV-A")
    from .conftest import PASSWORD, client
    c = client()
    assert c.post("/api/auth/login", json={"email": "a@example.test", "password": PASSWORD}).json()["next"] == "mfa"
    assert c.get("/api/me/summary").status_code == 401
    assert c.get("/api/fund/nav").status_code == 401
