from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # stored naive UTC


class User(Base):
    """A website login. Investors are linked to FrontierTradeLight data only
    through `investor_id` (the Fund Manager's InvestorID); names/emails from
    FrontierTradeLight never reach this database."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="investor")  # investor | admin
    status: Mapped[str] = mapped_column(String(16), default="invited")  # invited | active | disabled
    investor_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # TOTP secrets are encrypted at rest (see security.encrypt_secret).
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_pending_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_totp_step: Mapped[int] = mapped_column(Integer, default=0)  # replay protection

    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Server-side session. Only a SHA-256 of the cookie token is stored.
    stage: 'mfa' (password ok, awaiting TOTP), 'enroll' (must set up TOTP),
    'full' (fully authenticated)."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")

    user: Mapped[User] = relationship(back_populates="sessions")


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---- Fund data (replaced wholesale by each sync from FrontierTradeLight) ----

class NavPoint(Base):
    __tablename__ = "nav_points"
    __table_args__ = (UniqueConstraint("date", "generation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    nav: Mapped[float] = mapped_column(Float)
    generation: Mapped[int] = mapped_column(Integer, default=0)


class CapitalEvent(Base):
    __tablename__ = "capital_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    investor_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[date] = mapped_column(Date)
    type: Mapped[str] = mapped_column(String(16))  # DEPOSIT | WITHDRAWAL
    amount: Mapped[float] = mapped_column(Float)  # always positive, INR
    nav: Mapped[float] = mapped_column(Float)
    units: Mapped[float] = mapped_column(Float)  # signed: withdrawals negative
    seq: Mapped[int] = mapped_column(Integer, default=0)  # order within the source file


class FundState(Base):
    """Single-row table for fund-level scalars carried in the snapshot."""

    __tablename__ = "fund_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    current_generation: Mapped[int] = mapped_column(Integer, default=0)
    as_of: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    nav_points: Mapped[int] = mapped_column(Integer, default=0)
    investors: Mapped[int] = mapped_column(Integer, default=0)
    events: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16))  # applied | rejected
    message: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_email: Mapped[str] = mapped_column(String(254), default="")
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str] = mapped_column(String(128), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ip: Mapped[str] = mapped_column(String(64), default="")
