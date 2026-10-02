"""Schema and atomic apply for FrontierTradeLight snapshots.

The schema is strict: unknown fields are rejected (so names, emails,
holdings etc. can never ride along), and investor IDs must be the sync
script's pseudonyms, never raw FrontierTradeLight IDs (which are name slugs)."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete
from sqlalchemy.orm import Session as DB

from .models import CapitalEvent, FundState, NavPoint, SyncRun

PSEUDONYM = r"^inv_[0-9a-f]{20}$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NavIn(Strict):
    date: date
    nav: float = Field(gt=0)
    generation: int = Field(ge=0)


class EventIn(Strict):
    date: date
    type: Literal["DEPOSIT", "WITHDRAWAL"]
    amount: float = Field(gt=0)
    nav: float = Field(gt=0)
    units: float

    @model_validator(mode="after")
    def units_consistent(self):
        expected = self.amount / self.nav * (1 if self.type == "DEPOSIT" else -1)
        if abs(self.units - expected) > max(1e-6, abs(expected) * 1e-9):
            raise ValueError(f"units {self.units} inconsistent with amount/nav ({expected}) on {self.date}")
        return self


class InvestorIn(Strict):
    investor_id: str = Field(pattern=PSEUDONYM)
    events: list[EventIn] = Field(max_length=10_000)


class Snapshot(Strict):
    schema_version: Literal[1]
    generated_at: datetime
    currency: Literal["INR"]
    current_generation: int = Field(ge=0)
    nav_history: list[NavIn] = Field(max_length=50_000)
    investors: list[InvestorIn] = Field(max_length=2_000)

    @model_validator(mode="after")
    def unique_keys(self):
        keys = [(n.date, n.generation) for n in self.nav_history]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate (date, generation) in nav_history")
        ids = [i.investor_id for i in self.investors]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate investor_id")
        return self


def apply_snapshot(db: DB, snap: Snapshot, payload_sha256: str) -> SyncRun:
    """Replaces all fund data with the snapshot in one transaction, so
    readers see either the old data or the new, never a mix. Re-applying the
    same snapshot yields the same state (idempotent). Caller commits."""
    db.execute(delete(CapitalEvent))
    db.execute(delete(NavPoint))
    db.add_all(NavPoint(date=n.date, nav=n.nav, generation=n.generation) for n in snap.nav_history)
    seq = 0
    for inv in snap.investors:
        for e in inv.events:
            db.add(CapitalEvent(investor_id=inv.investor_id, date=e.date, type=e.type, amount=e.amount, nav=e.nav, units=e.units, seq=seq))
            seq += 1
    state = db.get(FundState, 1) or FundState(id=1)
    state.current_generation = snap.current_generation
    ga = snap.generated_at
    state.as_of = ga.astimezone(timezone.utc).replace(tzinfo=None) if ga.tzinfo else ga  # stored naive UTC
    db.merge(state)
    run = SyncRun(
        generated_at=state.as_of, schema_version=snap.schema_version, payload_sha256=payload_sha256,
        nav_points=len(snap.nav_history), investors=len(snap.investors), events=seq, status="applied",
    )
    db.add(run)
    return run
