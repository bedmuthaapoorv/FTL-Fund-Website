#!/usr/bin/env python3
"""
One-way, read-only export from FrontierTradeLight's Fund Manager to the
website. Runs on your machine; the website never connects back.

Reads ONLY:
  nav_history.csv     -> Date, NAV, Generation   (AUM/TotalUnits are ignored)
  capital_events.csv  -> Date, InvestorID, Type, Amount, NAV, Units
  generation.json     -> current generation number
Never opens investors.csv (names/emails), fund_holdings.csv, cash.json or
documents/.

InvestorIDs in FrontierTradeLight are derived from investor names, so each
one is replaced by a pseudonym: "inv_" + HMAC-SHA256(SYNC_ID_PEPPER, id).
The pepper stays on this machine and is never sent, so the server cannot
reverse the pseudonyms. Use --show-ids to see the local mapping when linking
website accounts.

Usage (from this folder):
  python3 export_snapshot.py              # dry run: validate + write out/snapshot.json
  python3 export_snapshot.py --show-ids   # print local InvestorID -> pseudonym map
  python3 export_snapshot.py --push       # sign and send to SYNC_URL

Standard library only, so it runs with any Python 3.10+.
"""

import argparse
import csv
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
HERE = Path(__file__).resolve().parent
DEFAULT_FUND_DIR = "/Users/apoorv/Projects/FrontierTradeLight/Strategies/Default/data/fund"


def load_env(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines); real env vars take precedence."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def config() -> dict:
    load_env(HERE / ".env")
    cfg = {
        "fund_dir": Path(os.environ.get("FTL_FUND_DIR", DEFAULT_FUND_DIR)),
        "url": os.environ.get("SYNC_URL", "http://localhost:8100/api/sync"),
        "secret": os.environ.get("SYNC_SECRET", ""),
        "pepper": os.environ.get("SYNC_ID_PEPPER", ""),
    }
    if len(cfg["pepper"]) < 32:
        sys.exit("SYNC_ID_PEPPER must be set (32+ chars) in sync/.env. See sync/.env.example.")
    return cfg


def pseudonym(pepper: str, investor_id: str) -> str:
    return "inv_" + hmac.new(pepper.encode(), investor_id.encode(), hashlib.sha256).hexdigest()[:20]


def _rows(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as f:  # read-only
        return list(csv.DictReader(f))


def build_snapshot(fund_dir: Path, pepper: str) -> tuple[dict, dict]:
    """Returns (snapshot, local_id_map). Raises ValueError on bad source data."""
    gen_path = fund_dir / "generation.json"
    current_generation = int(json.loads(gen_path.read_text())["generation"]) if gen_path.exists() else 0

    nav_history = []
    for r in _rows(fund_dir / "nav_history.csv"):
        gen = r.get("Generation", "")
        nav_history.append({
            "date": r["Date"],
            "nav": float(r["NAV"]),
            "generation": int(float(gen)) if gen not in ("", None) else 0,  # pre-generation rows = 0, as in FTL
        })

    id_map: dict[str, str] = {}
    by_investor: dict[str, list] = {}
    for r in _rows(fund_dir / "capital_events.csv"):
        raw_id = r["InvestorID"]
        pid = id_map.setdefault(raw_id, pseudonym(pepper, raw_id))
        typ = r["Type"].strip().upper()
        if typ not in ("DEPOSIT", "WITHDRAWAL"):
            raise ValueError(f"Unexpected capital event type: {typ!r}")
        by_investor.setdefault(pid, []).append({
            "date": r["Date"],
            "type": typ,
            "amount": float(r["Amount"]),
            "nav": float(r["NAV"]),
            "units": float(r["Units"]),
        })

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": "INR",
        "current_generation": current_generation,
        "nav_history": nav_history,
        "investors": [{"investor_id": pid, "events": ev} for pid, ev in by_investor.items()],
    }
    return snapshot, id_map


def sign(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def push(url: str, secret: str, body: bytes) -> dict:
    if len(secret) < 32:
        sys.exit("SYNC_SECRET must be set (32+ chars) and match the server's SYNC_SECRET.")
    host = urllib.parse.urlparse(url).hostname or ""
    if not url.startswith("https://") and host not in ("localhost", "127.0.0.1"):
        sys.exit("Refusing to push over plain HTTP to a non-local host.")
    ts = str(int(time.time()))
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "X-FTH-Timestamp": ts,
        "X-FTH-Signature": sign(secret, ts, body),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"Sync rejected ({e.code}): {e.read().decode(errors='replace')[:500]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--push", action="store_true", help="send the snapshot to SYNC_URL (default is a dry run)")
    ap.add_argument("--show-ids", action="store_true", help="print the local InvestorID -> pseudonym mapping")
    args = ap.parse_args()

    cfg = config()
    snapshot, id_map = build_snapshot(cfg["fund_dir"], cfg["pepper"])
    body = json.dumps(snapshot, separators=(",", ":")).encode()

    navs = snapshot["nav_history"]
    n_events = sum(len(i["events"]) for i in snapshot["investors"])
    print(f"Source:      {cfg['fund_dir']}")
    print(f"NAV points:  {len(navs)}" + (f"  ({navs[0]['date']} .. {navs[-1]['date']})" if navs else ""))
    print(f"Investors:   {len(snapshot['investors'])}   capital events: {n_events}   generation: {snapshot['current_generation']}")
    print(f"Payload:     {len(body):,} bytes, sha256 {hashlib.sha256(body).hexdigest()[:16]}…")

    if args.show_ids:
        print("\nLocal ID map (this machine only - do not share):")
        for raw, pid in sorted(id_map.items()):
            print(f"  {pid}  <-  {raw}")

    if not args.push:
        out = HERE / "out"
        out.mkdir(exist_ok=True)
        (out / "snapshot.json").write_text(json.dumps(snapshot, indent=2))
        print(f"\nDry run: wrote {out / 'snapshot.json'}. Re-run with --push to send.")
        return

    result = push(cfg["url"], cfg["secret"], body)
    print(f"\nPushed to {cfg['url']}: {result}")


if __name__ == "__main__":
    main()
