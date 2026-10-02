"""The FrontierTradeLight export script + signed sync endpoint, end to end,
using only FAKE fixture CSVs."""

import builtins
import csv
import hashlib
import importlib.util
import json
import pathlib
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models import SyncRun

from .conftest import login, make_user, SessionLocal

SCRIPT = Path(__file__).resolve().parents[2] / "sync" / "export_snapshot.py"
spec = importlib.util.spec_from_file_location("export_snapshot", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

SECRET = "test-sync-secret"
PEPPER = "fake-local-pepper-for-tests-only-0123456789"


def write_csv(path: Path, header: list[str], rows: list[list]):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


@pytest.fixture
def fund_dir(tmp_path):
    """A fake Fund Manager data folder shaped like FrontierTradeLight's."""
    write_csv(tmp_path / "investors.csv", ["InvestorID", "Name", "Email", "JoinDate"],
              [["fake_person_one", "Fake Person One", "one@example.test", "2026-01-01"]])
    write_csv(tmp_path / "nav_history.csv", ["Date", "AUM", "TotalUnits", "NAV", "Generation"],
              [["2026-01-01", 100000, 1000, 100.0, 1], ["2026-02-01", 110000, 1000, 110.0, 1]])
    write_csv(tmp_path / "capital_events.csv", ["Date", "InvestorID", "Type", "Amount", "NAV", "Units"],
              [["2026-01-01", "fake_person_one", "DEPOSIT", 100000, 100.0, 1000.0],
               ["2026-01-01", "fake_person_two", "DEPOSIT", 50000, 100.0, 500.0],
               ["2026-02-01", "fake_person_two", "WITHDRAWAL", 11000, 110.0, -100.0]])
    write_csv(tmp_path / "fund_holdings.csv", ["Symbol", "Qty", "AvgCost", "CurrentPrice"], [["FAKESYM", 1, 1, 1]])
    (tmp_path / "generation.json").write_text('{"generation": 1}')
    (tmp_path / "cash.json").write_text('{"amount": 1.0}')
    return tmp_path


def signed(body: bytes, ts: int | None = None, secret: str = SECRET) -> dict:
    t = str(ts if ts is not None else int(time.time()))
    return {"Content-Type": "application/json", "X-FTH-Timestamp": t, "X-FTH-Signature": exporter.sign(secret, t, body)}


def body_of(snapshot: dict) -> bytes:
    return json.dumps(snapshot, separators=(",", ":")).encode()


def bare() -> TestClient:
    return TestClient(app)  # the script sends no CSRF header or cookies


# ---- Export script ----

def test_export_reads_only_the_allowed_files(fund_dir, monkeypatch):
    opened: list[str] = []
    real_open, real_read = pathlib.Path.open, pathlib.Path.read_text
    monkeypatch.setattr(pathlib.Path, "open", lambda self, *a, **k: (opened.append(self.name), real_open(self, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: (opened.append(self.name), real_read(self, *a, **k))[1])
    real_builtin_open = builtins.open
    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (opened.append(Path(str(f)).name), real_builtin_open(f, *a, **k))[1])

    exporter.build_snapshot(fund_dir, PEPPER)
    assert set(opened) <= {"nav_history.csv", "capital_events.csv", "generation.json"}
    assert not {"investors.csv", "fund_holdings.csv", "cash.json"} & set(opened)


def test_export_pseudonymises_ids_and_strips_sensitive_fields(fund_dir):
    snap, id_map = exporter.build_snapshot(fund_dir, PEPPER)
    raw = json.dumps(snap)
    for secret_text in ("fake_person_one", "fake_person_two", "Fake Person", "example.test", "AUM", "TotalUnits", "FAKESYM"):
        assert secret_text not in raw
    assert set(id_map) == {"fake_person_one", "fake_person_two"}
    assert all(i["investor_id"].startswith("inv_") for i in snap["investors"])
    # Deterministic for a given pepper, different for another.
    assert exporter.build_snapshot(fund_dir, PEPPER)[1] == id_map
    assert exporter.build_snapshot(fund_dir, PEPPER + "x")[1] != id_map


# ---- Signed push ----

def test_signed_push_applies_and_investor_sees_own_data(fund_dir):
    snap, id_map = exporter.build_snapshot(fund_dir, PEPPER)
    body = body_of(snap)
    r = bare().post("/api/sync", content=body, headers=signed(body))
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "applied", "nav_points": 2, "investors": 2, "events": 3}

    uid, secret = make_user("one@example.test", investor_id=id_map["fake_person_one"])
    s = login("one@example.test", uid, secret).get("/api/me/summary").json()
    assert s["units"] == 1000 and s["nav"] == 110.0 and s["current_value"] == 110000


def test_push_is_idempotent_and_replaces_data(fund_dir):
    snap, _ = exporter.build_snapshot(fund_dir, PEPPER)
    body = body_of(snap)
    for _ in range(2):
        assert bare().post("/api/sync", content=body, headers=signed(body)).json()["events"] == 3
    snap["investors"] = snap["investors"][:1]
    smaller = body_of(snap)
    assert bare().post("/api/sync", content=smaller, headers=signed(smaller)).json()["events"] == 1


def test_bad_signature_rejected(fund_dir):
    body = body_of(exporter.build_snapshot(fund_dir, PEPPER)[0])
    assert bare().post("/api/sync", content=body, headers=signed(body, secret="wrong-secret")).status_code == 401
    h = signed(body)
    assert bare().post("/api/sync", content=body + b" ", headers=h).status_code == 401  # body tampered


def test_stale_or_missing_timestamp_rejected(fund_dir):
    body = body_of(exporter.build_snapshot(fund_dir, PEPPER)[0])
    assert bare().post("/api/sync", content=body, headers=signed(body, ts=int(time.time()) - 3600)).status_code == 401
    assert bare().post("/api/sync", content=body, headers={"Content-Type": "application/json"}).status_code == 401


@pytest.mark.parametrize("mutate", [
    lambda s: s["investors"][0].update(name="Leaked Name"),          # unknown field
    lambda s: s.update(holdings=[{"symbol": "X"}]),                  # unknown top-level field
    lambda s: s["investors"][0].update(investor_id="fake_person_one"),  # raw, un-pseudonymised ID
    lambda s: s["investors"][0]["events"][0].update(units=999.0),    # inconsistent units
    lambda s: s.update(currency="USD"),
    lambda s: s.update(schema_version=2),
])
def test_invalid_snapshots_rejected_and_recorded(fund_dir, mutate):
    snap, _ = exporter.build_snapshot(fund_dir, PEPPER)
    mutate(snap)
    body = body_of(snap)
    r = bare().post("/api/sync", content=body, headers=signed(body))
    assert r.status_code == 422, r.text
    with SessionLocal() as s:
        runs = list(s.scalars(select(SyncRun)))
    assert [x.status for x in runs] == ["rejected"]
    assert runs[0].payload_sha256 == hashlib.sha256(body).hexdigest()


def test_rejected_push_leaves_existing_data_untouched(fund_dir):
    snap, _ = exporter.build_snapshot(fund_dir, PEPPER)
    good = body_of(snap)
    bare().post("/api/sync", content=good, headers=signed(good))
    snap["investors"][0]["events"][0]["units"] = 1.0
    bad = body_of(snap)
    assert bare().post("/api/sync", content=bad, headers=signed(bad)).status_code == 422
    from app.models import CapitalEvent
    with SessionLocal() as s:
        assert len(list(s.scalars(select(CapitalEvent)))) == 3


def test_admin_upload_requires_admin(fund_dir):
    body = body_of(exporter.build_snapshot(fund_dir, PEPPER)[0])
    uid, secret = make_user("inv@example.test", investor_id=None)
    inv = login("inv@example.test", uid, secret)
    assert inv.post("/api/admin/sync/upload", content=body).status_code == 403
    aid, asecret = make_user("admin@example.test", role="admin")
    admin = login("admin@example.test", aid, asecret)
    assert admin.post("/api/admin/sync/upload", content=body).json()["status"] == "applied"
