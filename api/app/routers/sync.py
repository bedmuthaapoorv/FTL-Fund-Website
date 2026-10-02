import hashlib
import hmac
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session as DB

from ..audit import audit
from ..config import get_settings
from ..db import get_db
from ..models import SyncRun
from ..ratelimit import limiter
from ..snapshot import Snapshot, apply_snapshot

router = APIRouter(prefix="/api", tags=["sync"])

MAX_BODY = 5 * 1024 * 1024
MAX_SKEW_SECONDS = 300


def _reject(db: DB, sha: str, message: str, status: int) -> HTTPException:
    db.rollback()
    db.add(SyncRun(schema_version=0, payload_sha256=sha, status="rejected", message=message[:2000]))
    db.commit()
    return HTTPException(status, message)


def validate_and_apply(db: DB, body: bytes, request: Request, actor=None) -> dict:
    sha = hashlib.sha256(body).hexdigest()
    try:
        snap = Snapshot.model_validate(json.loads(body))
    except (ValueError, ValidationError) as e:
        detail = e.errors(include_url=False, include_input=False) if isinstance(e, ValidationError) else str(e)
        raise _reject(db, sha, f"Invalid snapshot: {json.dumps(detail, default=str)[:1500]}", 422)
    run = apply_snapshot(db, snap, sha)
    audit(db, request, "sync.applied", actor, target=sha[:16], nav_points=run.nav_points, investors=run.investors, events=run.events,
          via="admin_upload" if actor else "signed_push")
    db.commit()
    return {"status": "applied", "nav_points": run.nav_points, "investors": run.investors, "events": run.events}


@router.post("/sync")
@limiter.limit("30/hour")
async def sync(request: Request, db: DB = Depends(get_db)):
    """Signed push from the local export script. Authenticated by HMAC over
    timestamp + body with SYNC_SECRET; no cookies or sessions involved."""
    secret = get_settings().sync_secret
    if len(secret) < 16:
        raise HTTPException(503, "Sync is not configured.")
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "Snapshot too large.")
    ts = request.headers.get("x-fth-timestamp", "")
    sig = request.headers.get("x-fth-signature", "")
    if not ts.isdigit() or abs(time.time() - int(ts)) > MAX_SKEW_SECONDS:
        raise HTTPException(401, "Missing or stale timestamp.")
    expected = hmac.new(secret.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(401, "Bad signature.")
    return validate_and_apply(db, body, request)
