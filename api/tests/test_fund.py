"""Fund maths must match FrontierTradeLight's fund_manager_utils exactly."""

from datetime import date

import pytest

from app import fund
from app.models import CapitalEvent, FundState, NavPoint

from .conftest import SessionLocal


def ev(inv, d, typ, amount, nav, seq=0):
    units = amount / nav if typ == "DEPOSIT" else -(amount / nav)
    return CapitalEvent(investor_id=inv, date=d, type=typ, amount=amount, nav=nav, units=units, seq=seq)


def test_return_matches_frontiertradelight_definition():
    events = [ev("X", date(2026, 1, 1), "DEPOSIT", 100000, 100), ev("X", date(2026, 3, 1), "WITHDRAWAL", 22000, 110)]
    s = fund.summarize(events, nav=120.0)
    assert s["units"] == pytest.approx(800)
    assert s["current_value"] == pytest.approx(96000)
    assert s["net_contributed"] == pytest.approx(78000)
    # (value - net contributed) / net contributed
    assert s["return_pct"] == pytest.approx((96000 - 78000) / 78000 * 100)


def test_no_return_when_nothing_net_contributed():
    events = [ev("X", date(2026, 1, 1), "DEPOSIT", 100, 100), ev("X", date(2026, 2, 1), "WITHDRAWAL", 150, 150)]
    assert fund.summarize(events, 150.0)["return_pct"] is None
    assert fund.summarize(events, 150.0)["units"] == 0.0  # float noise snapped


def test_latest_nav_uses_current_generation_only():
    with SessionLocal() as s:
        s.add(FundState(id=1, current_generation=2))
        s.add_all([
            NavPoint(date=date(2025, 12, 1), nav=150.0, generation=1),  # newer-looking old era must be ignored
            NavPoint(date=date(2025, 6, 1), nav=101.0, generation=2),
        ])
        s.add(ev("X", date(2025, 6, 1), "DEPOSIT", 1000, 100))
        s.commit()
        assert fund.latest_nav(s) == 101.0


def test_latest_nav_is_base_when_no_units_outstanding():
    with SessionLocal() as s:
        s.add(FundState(id=1, current_generation=1))
        s.add(NavPoint(date=date(2026, 1, 1), nav=130.0, generation=1))
        s.add_all([ev("X", date(2026, 1, 1), "DEPOSIT", 1000, 100), ev("X", date(2026, 2, 1), "WITHDRAWAL", 1000, 100)])
        s.commit()
        assert fund.latest_nav(s) == fund.BASE_NAV
