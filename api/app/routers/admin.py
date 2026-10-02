from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from ..db import get_db
from ..deps import require_admin
from ..models import User

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users")
def list_users(db: DB = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.role, User.email)).all()
    return [
        {
            "id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role, "status": u.status,
            "investor_id": u.investor_id, "mfa_enabled": u.mfa_enabled,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]
