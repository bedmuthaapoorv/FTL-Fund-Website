from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DB

from .audit import client_ip
from .config import get_settings
from .models import Session, User, utcnow
from .security import new_token, sha256

COOKIE = "fth_session"


def start_session(db: DB, response: Response, request: Request, user: User, stage: str) -> Session:
    """Creates a fresh session (never reuses a token across a privilege
    change, preventing session fixation) and sets the cookie."""
    s = get_settings()
    token = new_token()
    now = utcnow()
    lifetime = timedelta(minutes=s.mfa_step_minutes) if stage != "full" else timedelta(hours=s.session_absolute_hours)
    sess = Session(
        token_hash=sha256(token),
        user_id=user.id,
        stage=stage,
        created_at=now,
        last_seen_at=now,
        expires_at=now + lifetime,
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:256],
    )
    db.add(sess)
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=s.secure_cookies,
        samesite="strict",
        path="/api",
        max_age=int(lifetime.total_seconds()),
    )
    return sess


def end_session(db: DB, response: Response, sess: Session | None) -> None:
    if sess is not None:
        db.delete(sess)
    response.delete_cookie(COOKIE, path="/api", samesite="strict", secure=get_settings().secure_cookies, httponly=True)


def end_all_sessions(db: DB, user_id: int) -> None:
    db.execute(delete(Session).where(Session.user_id == user_id))


def load_session(db: DB, request: Request) -> Session | None:
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    sess = db.scalar(select(Session).where(Session.token_hash == sha256(token)))
    if sess is None:
        return None
    now = utcnow()
    idle = timedelta(minutes=get_settings().session_idle_minutes)
    if now >= sess.expires_at or (sess.stage == "full" and now - sess.last_seen_at > idle):
        db.delete(sess)
        db.commit()
        return None
    if sess.user.status != "active":
        return None
    if (now - sess.last_seen_at).total_seconds() > 30:
        sess.last_seen_at = now
        db.commit()
    return sess
