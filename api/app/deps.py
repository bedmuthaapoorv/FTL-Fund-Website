from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DB

from .db import get_db
from .models import Session, User
from .scope import InvestorScope
from .sessions import load_session


def optional_session(request: Request, db: DB = Depends(get_db)) -> Session | None:
    return load_session(db, request)


def session_at(stage: str):
    def dep(sess: Session | None = Depends(optional_session)) -> Session:
        if sess is None or sess.stage != stage:
            raise HTTPException(401, "Not signed in.")
        return sess

    return dep


def require_user(sess: Session = Depends(session_at("full"))) -> User:
    return sess.user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Forbidden.")
    return user


def require_investor(user: User = Depends(require_user), db: DB = Depends(get_db)) -> InvestorScope:
    """The ONLY way investor-facing routes get data access. The scope is
    bound to the signed-in user's own investor_id; nothing in the request
    (path, query or body) can change it."""
    if user.role != "investor":
        raise HTTPException(403, "Forbidden.")
    return InvestorScope(db, user.investor_id)
