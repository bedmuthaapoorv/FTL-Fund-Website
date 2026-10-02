"""Fund-level calculations. Deliberately mirrors FrontierTradeLight's
fund_manager_utils (latest_nav / investor_summary) so both systems always
agree on a number."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from .models import CapitalEvent, FundState, NavPoint

BASE_NAV = 100.0
UNITS_EPSILON = 1e-6


def snap(x: float) -> float:
    return 0.0 if abs(x) < UNITS_EPSILON else x


def fund_state(db: DB) -> FundState:
    return db.get(FundState, 1) or FundState(id=1, current_generation=0, as_of=None)


def total_units_outstanding(db: DB) -> float:
    return snap(float(db.scalar(select(func.coalesce(func.sum(CapitalEvent.units), 0.0)))))


def latest_nav(db: DB) -> float:
    """Latest NAV in the current generation, or BASE_NAV when the fund has
    no units outstanding or the generation has no NAV yet."""
    if total_units_outstanding(db) == 0.0:
        return BASE_NAV
    gen = fund_state(db).current_generation
    nav = db.scalar(
        select(NavPoint.nav).where(NavPoint.generation == gen).order_by(NavPoint.date.desc()).limit(1)
    )
    return float(nav) if nav is not None else BASE_NAV


def nav_series(db: DB) -> list[dict]:
    rows = db.scalars(select(NavPoint).order_by(NavPoint.generation, NavPoint.date)).all()
    return [{"date": r.date.isoformat(), "nav": r.nav, "generation": r.generation} for r in rows]


def summarize(events: list[CapitalEvent], nav: float) -> dict:
    units = snap(sum(e.units for e in events))
    deposited = sum(e.amount for e in events if e.type == "DEPOSIT")
    withdrawn = sum(e.amount for e in events if e.type == "WITHDRAWAL")
    net = deposited - withdrawn
    value = units * nav
    return {
        "units": units,
        "nav": nav,
        "current_value": value,
        "total_deposited": deposited,
        "total_withdrawn": withdrawn,
        "net_contributed": net,
        # Same definition as FrontierTradeLight: gain over net capital contributed.
        "return_pct": ((value - net) / net * 100) if net > 0 else None,
        "first_investment": min((e.date for e in events), default=None),
    }
