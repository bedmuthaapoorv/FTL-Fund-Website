from datetime import timedelta

import segno
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DB

from ..audit import audit
from ..config import get_settings
from ..db import get_db
from ..deps import optional_session, session_at
from ..models import Invite, RecoveryCode, Session, User, utcnow
from ..ratelimit import limiter
from ..security import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    new_recovery_codes,
    new_totp_secret,
    normalize_recovery_code,
    password_problem,
    sha256,
    totp_uri,
    verify_password,
    verify_totp,
)
from ..sessions import end_all_sessions, end_session, start_session

router = APIRouter(prefix="/api/auth", tags=["auth"])

GENERIC_LOGIN_ERROR = "Invalid email or password."


def _limit():
    return get_settings().login_rate_limit


def _register_failure(db: DB, user: User) -> None:
    s = get_settings()
    user.failed_logins += 1
    if user.failed_logins >= s.lockout_threshold:
        user.locked_until = utcnow() + timedelta(minutes=s.lockout_minutes)
        user.failed_logins = 0


def _is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > utcnow()


# ---- Invites ----

class InviteToken(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class InviteAccept(InviteToken):
    password: str = Field(min_length=1, max_length=256)


def _valid_invite(db: DB, token: str) -> Invite:
    inv = db.scalar(select(Invite).where(Invite.token_hash == sha256(token)))
    if inv is None or inv.used_at is not None or inv.expires_at <= utcnow():
        raise HTTPException(400, "This invitation link is invalid or has expired. Please ask for a new one.")
    return inv


@router.post("/invite/check")
@limiter.limit(_limit)
def invite_check(request: Request, body: InviteToken, db: DB = Depends(get_db)):
    inv = _valid_invite(db, body.token)
    user = db.get(User, inv.user_id)
    return {"email": user.email}


@router.post("/invite/accept")
@limiter.limit(_limit)
def invite_accept(request: Request, response: Response, body: InviteAccept, db: DB = Depends(get_db)):
    inv = _valid_invite(db, body.token)
    user = db.get(User, inv.user_id)
    if user.status == "disabled":
        raise HTTPException(400, "This invitation link is invalid or has expired. Please ask for a new one.")
    if problem := password_problem(body.password, user.email):
        raise HTTPException(400, problem)

    inv.used_at = utcnow()
    user.password_hash = hash_password(body.password)
    user.status = "active"
    # Accepting an invite always (re)starts MFA enrolment from scratch.
    user.mfa_enabled = False
    user.totp_secret_enc = None
    user.totp_pending_enc = None
    user.failed_logins = 0
    user.locked_until = None
    end_all_sessions(db, user.id)
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    start_session(db, response, request, user, "enroll")
    audit(db, request, "auth.invite_accepted", user, target=user.email)
    db.commit()
    return {"next": "enroll"}


# ---- Password step ----

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
@limiter.limit(_limit)
def login(request: Request, response: Response, body: LoginIn, db: DB = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    if user is None or user.status != "active" or _is_locked(user):
        verify_password(body.password, None)  # equalise timing
        if user is not None:
            audit(db, request, "auth.login_refused", user, target=user.email, reason=user.status if user.status != "active" else "locked")
            db.commit()
        raise HTTPException(401, GENERIC_LOGIN_ERROR)
    if not verify_password(body.password, user.password_hash):
        _register_failure(db, user)
        audit(db, request, "auth.login_failed", user, target=user.email)
        db.commit()
        raise HTTPException(401, GENERIC_LOGIN_ERROR)

    if not user.mfa_enabled:
        # MFA enrolment is only reachable through a fresh invite link. Otherwise
        # anyone holding just the password could register their own authenticator.
        raise HTTPException(401, "Two-step verification is not set up for this account. Please ask for a new invitation.")
    start_session(db, response, request, user, "mfa")
    db.commit()
    return {"next": "mfa"}


# ---- TOTP enrolment ----

@router.get("/mfa/setup")
def mfa_setup(sess: Session = Depends(session_at("enroll")), db: DB = Depends(get_db)):
    user = sess.user
    if not user.totp_pending_enc:
        user.totp_pending_enc = encrypt_secret(new_totp_secret())
        db.commit()
    secret = decrypt_secret(user.totp_pending_enc)
    uri = totp_uri(secret, user.email)
    svg = segno.make(uri, error="m").svg_inline(scale=5, border=2, dark="#111318", light="#ffffff")
    return {"secret": secret, "uri": uri, "qr_svg": svg}


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=12)


@router.post("/mfa/enroll")
@limiter.limit(_limit)
def mfa_enroll(request: Request, response: Response, body: CodeIn, sess: Session = Depends(session_at("enroll")), db: DB = Depends(get_db)):
    user = sess.user
    if not user.totp_pending_enc:
        raise HTTPException(400, "Start set-up again.")
    secret = decrypt_secret(user.totp_pending_enc)
    step = verify_totp(secret, body.code, 0)
    if step is None:
        raise HTTPException(400, "That code is not correct. Check your authenticator app's clock and try again.")

    user.totp_secret_enc = user.totp_pending_enc
    user.totp_pending_enc = None
    user.mfa_enabled = True
    user.last_totp_step = step
    user.last_login_at = utcnow()

    codes = new_recovery_codes()
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    for c in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=sha256(c)))

    end_session(db, response, sess)
    start_session(db, response, request, user, "full")
    audit(db, request, "auth.mfa_enrolled", user, target=user.email)
    db.commit()
    return {"recovery_codes": codes, "role": user.role}


# ---- TOTP / recovery-code verification ----

class VerifyIn(BaseModel):
    code: str | None = Field(default=None, max_length=12)
    recovery_code: str | None = Field(default=None, max_length=20)


@router.post("/mfa/verify")
@limiter.limit(_limit)
def mfa_verify(request: Request, response: Response, body: VerifyIn, sess: Session = Depends(session_at("mfa")), db: DB = Depends(get_db)):
    user = sess.user
    if _is_locked(user):
        raise HTTPException(401, "Too many attempts. Please try again later.")

    ok = False
    used_recovery = False
    if body.code:
        step = verify_totp(decrypt_secret(user.totp_secret_enc), body.code, user.last_totp_step)
        if step is not None:
            user.last_totp_step = step
            ok = True
    elif body.recovery_code:
        rc = db.scalar(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user.id,
                RecoveryCode.code_hash == sha256(normalize_recovery_code(body.recovery_code)),
                RecoveryCode.used_at.is_(None),
            )
        )
        if rc is not None:
            rc.used_at = utcnow()
            ok = used_recovery = True

    if not ok:
        _register_failure(db, user)
        audit(db, request, "auth.mfa_failed", user, target=user.email)
        db.commit()
        raise HTTPException(401, "That code is not correct.")

    user.failed_logins = 0
    user.last_login_at = utcnow()
    end_session(db, response, sess)
    start_session(db, response, request, user, "full")
    audit(db, request, "auth.login", user, target=user.email, recovery_code=used_recovery)
    db.commit()
    remaining = db.scalar(select(func.count()).where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None)))
    return {"role": user.role, "recovery_codes_remaining": remaining}


# ---- Session ----

@router.get("/me")
def me(sess: Session | None = Depends(optional_session)):
    if sess is None:
        raise HTTPException(401, "Not signed in.")
    u = sess.user
    return {"stage": sess.stage, "email": u.email, "role": u.role, "display_name": u.display_name}


@router.post("/logout")
def logout(response: Response, sess: Session | None = Depends(optional_session), db: DB = Depends(get_db)):
    end_session(db, response, sess)
    db.commit()
    return {"ok": True}
