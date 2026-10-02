"""Per-investor data access. Every investor-facing query goes through
InvestorScope, which is constructed only by deps.require_investor from the
signed-in user. Each method filters by the bound investor_id, so a request
can never widen its own view by supplying another ID."""

from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from . import fund
from .models import CapitalEvent


class InvestorScope:
    def __init__(self, db: DB, investor_id: str | None):
        self._db = db
        self.investor_id = investor_id  # None => account not yet linked: sees nothing

    @property
    def linked(self) -> bool:
        return self.investor_id is not None

    def events(self) -> list[CapitalEvent]:
        if not self.linked:
            return []
        q = select(CapitalEvent).where(CapitalEvent.investor_id == self.investor_id).order_by(CapitalEvent.date, CapitalEvent.seq)
        return list(self._db.scalars(q))

    def event(self, event_id: int) -> CapitalEvent | None:
        if not self.linked:
            return None
        q = select(CapitalEvent).where(CapitalEvent.id == event_id, CapitalEvent.investor_id == self.investor_id)
        return self._db.scalar(q)

    def summary(self) -> dict:
        return fund.summarize(self.events(), fund.latest_nav(self._db))
