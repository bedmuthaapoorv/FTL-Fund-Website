from fastapi import Request
from sqlalchemy.orm import Session as DB

from .models import AuditLog, User


def client_ip(request: Request | None) -> str:
    return (request.client.host if request and request.client else "")[:64]


def audit(db: DB, request: Request | None, action: str, actor: User | None = None, target: str = "", **detail) -> None:
    """Append-only record of admin and security-relevant actions. Callers
    commit as part of their own transaction so the log can't diverge from
    what actually happened."""
    db.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_email=actor.email if actor else "",
            action=action,
            target=target[:128],
            detail=detail,
            ip=client_ip(request),
        )
    )
