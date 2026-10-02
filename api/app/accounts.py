from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session as DB

from .config import get_settings
from .models import Invite, User, utcnow
from .security import new_token, sha256


def issue_invite(db: DB, user: User) -> str:
    """Creates a single-use invite and returns its plaintext link. Any
    earlier unused invites for the user are invalidated. The token goes in
    the URL fragment, so it is never sent to servers or leaked via Referer."""
    s = get_settings()
    now = utcnow()
    db.execute(update(Invite).where(Invite.user_id == user.id, Invite.used_at.is_(None)).values(used_at=now))
    token = new_token()
    db.add(Invite(user_id=user.id, token_hash=sha256(token), expires_at=now + timedelta(hours=s.invite_valid_hours)))
    return f"{s.site_url}/invite#token={token}"
