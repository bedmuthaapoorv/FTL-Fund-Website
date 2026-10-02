from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DB

from .. import fund
from ..db import get_db
from ..deps import require_investor, require_user
from ..models import CapitalEvent, User
from ..scope import InvestorScope

router = APIRouter(prefix="/api", tags=["investor"])


def _event(e: CapitalEvent) -> dict:
    return {"id": e.id, "date": e.date.isoformat(), "type": e.type, "amount": e.amount, "nav": e.nav, "units": e.units}


# NB: no route here accepts an investor ID. Scope comes only from the session.

@router.get("/me/summary")
def my_summary(scope: InvestorScope = Depends(require_investor), db: DB = Depends(get_db)):
    s = scope.summary()
    if s["first_investment"]:
        s["first_investment"] = s["first_investment"].isoformat()
    st = fund.fund_state(db)
    return {**s, "linked": scope.linked, "as_of": st.as_of.isoformat() if st.as_of else None, "currency": "INR"}


@router.get("/me/events")
def my_events(scope: InvestorScope = Depends(require_investor)):
    return [_event(e) for e in scope.events()]


@router.get("/me/events/{event_id}")
def my_event(event_id: int, scope: InvestorScope = Depends(require_investor)):
    e = scope.event(event_id)
    if e is None:
        raise HTTPException(404, "Not found.")  # same response whether it exists for someone else or not at all
    return _event(e)


@router.get("/fund/nav")
def fund_nav(_: User = Depends(require_user), db: DB = Depends(get_db)):
    """Fund-wide NAV history: identical for every investor, so any fully
    signed-in user may read it."""
    return {"current_generation": fund.fund_state(db).current_generation, "points": fund.nav_series(db)}
