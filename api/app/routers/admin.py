from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DB

from .. import fund
from ..accounts import issue_invite
from ..audit import audit
from ..db import get_db
from ..deps import require_admin
from ..models import AuditLog, CapitalEvent, RecoveryCode, SyncRun, User
from ..sessions import end_all_sessions
from .sync import MAX_BODY, validate_and_apply

# Every route here requires a fully authenticated admin; every write is audited.
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

INVESTOR_ID = r"^[A-Za-z0-9_.-]{1,64}$"


def _user(u: User) -> dict:
    return {
        "id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role, "status": u.status,
        "investor_id": u.investor_id, "mfa_enabled": u.mfa_enabled,
        "created_at": u.created_at.isoformat(),
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def _get(db: DB, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "Not found.")
    return u


def _check_investor_id(db: DB, investor_id: str | None, exclude_user: int | None = None) -> None:
    if investor_id is None:
        return
    clash = db.scalar(select(User).where(User.investor_id == investor_id, User.id != (exclude_user or -1)))
    if clash:
        raise HTTPException(409, f"That investor ID is already linked to {clash.email}.")


@router.get("/users")
def list_users(db: DB = Depends(get_db)):
    return [_user(u) for u in db.scalars(select(User).order_by(User.role.desc(), User.email))]


@router.get("/investor-ids")
def investor_ids(db: DB = Depends(get_db)):
    """Investor IDs present in the synced data, with their position and
    which account (if any) they're linked to."""
    nav = fund.latest_nav(db)
    linked = {u.investor_id: u.email for u in db.scalars(select(User).where(User.investor_id.is_not(None)))}
    out = []
    for (iid,) in db.execute(select(CapitalEvent.investor_id).distinct().order_by(CapitalEvent.investor_id)):
        evs = list(db.scalars(select(CapitalEvent).where(CapitalEvent.investor_id == iid)))
        s = fund.summarize(evs, nav)
        out.append({"investor_id": iid, "units": s["units"], "current_value": s["current_value"], "linked_to": linked.get(iid)})
    return out


class CreateUser(BaseModel):
    email: EmailStr
    display_name: str = Field(default="", max_length=120)
    role: str = Field(default="investor", pattern="^(investor|admin)$")
    investor_id: str | None = Field(default=None, pattern=INVESTOR_ID)


@router.post("/users")
def create_user(body: CreateUser, request: Request, admin: User = Depends(require_admin), db: DB = Depends(get_db)):
    email = str(body.email).strip().lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "A user with that email already exists.")
    if body.role == "admin" and body.investor_id:
        raise HTTPException(400, "Admin accounts cannot be linked to an investor ID.")
    _check_investor_id(db, body.investor_id)
    u = User(email=email, display_name=body.display_name.strip(), role=body.role, status="invited", investor_id=body.investor_id)
    db.add(u)
    db.flush()
    link = issue_invite(db, u)
    audit(db, request, "admin.user_created", admin, target=email, role=body.role, investor_id=body.investor_id)
    db.commit()
    return {"user": _user(u), "invite_link": link}


class UpdateUser(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    investor_id: str | None = Field(default=None, pattern=INVESTOR_ID)
    unlink: bool = False
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UpdateUser, request: Request, admin: User = Depends(require_admin), db: DB = Depends(get_db)):
    u = _get(db, user_id)
    changes: dict = {}
    if body.display_name is not None and body.display_name.strip() != u.display_name:
        changes["display_name"] = [u.display_name, body.display_name.strip()]
        u.display_name = body.display_name.strip()
    if body.unlink or body.investor_id is not None:
        new_id = None if body.unlink else body.investor_id
        if new_id and u.role != "investor":
            raise HTTPException(400, "Only investor accounts can be linked.")
        _check_investor_id(db, new_id, exclude_user=u.id)
        if new_id != u.investor_id:
            changes["investor_id"] = [u.investor_id, new_id]
            u.investor_id = new_id
    if body.status is not None and body.status != u.status:
        if u.id == admin.id:
            raise HTTPException(400, "You cannot change your own status.")
        if body.status == "active" and u.status == "invited":
            raise HTTPException(400, "Invited users become active by accepting their invitation.")
        changes["status"] = [u.status, body.status]
        u.status = body.status
        if body.status == "disabled":
            end_all_sessions(db, u.id)
    if changes:
        audit(db, request, "admin.user_updated", admin, target=u.email, changes=changes)
    db.commit()
    return _user(u)


@router.post("/users/{user_id}/reset-access")
def reset_access(user_id: int, request: Request, admin: User = Depends(require_admin), db: DB = Depends(get_db)):
    """Revokes password, MFA, recovery codes and sessions, and issues a new
    invite. Used for lost devices, suspected compromise, or expired invites."""
    u = _get(db, user_id)
    if u.id == admin.id:
        raise HTTPException(400, "Use the CLI to reset your own access.")
    u.password_hash = None
    u.totp_secret_enc = None
    u.totp_pending_enc = None
    u.mfa_enabled = False
    u.status = "invited"
    end_all_sessions(db, u.id)
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == u.id))
    link = issue_invite(db, u)
    audit(db, request, "admin.access_reset", admin, target=u.email)
    db.commit()
    return {"user": _user(u), "invite_link": link}


@router.get("/sync-runs")
def sync_runs(db: DB = Depends(get_db)):
    runs = db.scalars(select(SyncRun).order_by(SyncRun.id.desc()).limit(50))
    st = fund.fund_state(db)
    return {
        "as_of": st.as_of.isoformat() if st.as_of else None,
        "current_generation": st.current_generation,
        "runs": [
            {"id": r.id, "received_at": r.received_at.isoformat(), "generated_at": r.generated_at.isoformat() if r.generated_at else None,
             "status": r.status, "nav_points": r.nav_points, "investors": r.investors, "events": r.events,
             "payload_sha256": r.payload_sha256[:16], "message": r.message}
            for r in runs
        ],
    }


@router.post("/sync/upload")
async def sync_upload(request: Request, admin: User = Depends(require_admin), db: DB = Depends(get_db)):
    """Alternative to the signed push: upload sync/out/snapshot.json from the
    browser. Same validation and atomic apply."""
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "Snapshot too large.")
    return validate_and_apply(db, body, request, actor=admin)


@router.get("/audit")
def audit_log(before: int | None = Query(default=None), limit: int = Query(default=100, le=500), db: DB = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if before:
        q = q.where(AuditLog.id < before)
    return [
        {"id": a.id, "at": a.at.isoformat(), "actor": a.actor_email, "action": a.action, "target": a.target, "detail": a.detail, "ip": a.ip}
        for a in db.scalars(q)
    ]
