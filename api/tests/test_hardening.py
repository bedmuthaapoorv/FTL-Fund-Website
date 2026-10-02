import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app, create_app


def test_api_security_headers():
    r = TestClient(app).get("/api/health")
    assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in r.headers  # only in prod


def test_production_refuses_unsafe_config():
    bad = Settings(env="prod", site_url="http://x", data_encryption_key="", sync_secret="short", database_url="sqlite:///x.db")
    problems = bad.production_problems()
    assert len(problems) == 5
    good = Settings(
        env="prod", site_url="https://fund.example", data_encryption_key="k", sync_secret="s" * 40,
        database_url="postgresql+psycopg://u:p@h/db", email_backend="smtp", smtp_password="app-password",
    )
    assert good.production_problems() == []


@pytest.fixture
def site_client(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("SHELL")
    (dist / "approach.html").write_text("APPROACH")
    (dist / "legal").mkdir()
    (dist / "legal" / "risk.html").write_text("RISK")
    (dist / "assets" / "app.js").write_text("js")
    (dist / "csp-hashes.json").write_text(json.dumps(["'sha256-abc='"]))
    (tmp_path / "secret.txt").write_text("SECRET")
    monkeypatch.setenv("STATIC_DIR", str(dist))
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def test_static_site_routes_and_headers(site_client):
    home = site_client.get("/")
    assert home.status_code == 200 and home.text == "SHELL"
    r = site_client.get("/approach")
    assert r.status_code == 200 and r.text == "APPROACH"
    csp = r.headers["content-security-policy"]
    assert "script-src 'self' 'sha256-abc='" in csp and "unsafe-inline" not in csp.split("style-src-attr")[0]
    assert "frame-ancestors 'none'" in csp
    assert site_client.get("/legal/risk").text == "RISK"
    assert site_client.get("/assets/app.js").headers["cache-control"].endswith("immutable")


def test_static_site_never_escapes_dist_or_shadows_api(site_client):
    for path in ("/../secret.txt", "/..%2Fsecret.txt", "/%2e%2e/secret.txt"):
        r = site_client.get(path)
        assert "SECRET" not in r.text
    r = site_client.get("/no-such-page")
    assert r.status_code == 404 and r.text == "SHELL"
    assert site_client.get("/csp-hashes.json").text == "SHELL"
    r = site_client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/json")
