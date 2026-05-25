"""DCA 规划器单元测试（M4）：联动 multiplier、非交易日顺延、频率展开。"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import (
    DCAExecution,
    DCAPlan,
    IndexMeta,
    IndexQuote,
    Market,
    ThresholdOverride,
    TradingCalendar,
    Valuation,
)
from app.services.dca_planner import (
    compute_multiplier,
    refresh_executions_for_plan,
    upcoming_scheduled_dates,
)
from app.utils.time_utils import now_iso
from app.valuation import (
    TIER_EXTREME_HIGH,
    TIER_EXTREME_LOW,
    TIER_FAIR,
    TIER_HIGH,
    TIER_LOW,
)


def test_multiplier_default_mapping():
    assert compute_multiplier(TIER_EXTREME_LOW) == Decimal("2.0")
    assert compute_multiplier(TIER_LOW) == Decimal("2.0")
    assert compute_multiplier(TIER_FAIR) == Decimal("1.0")
    assert compute_multiplier(TIER_HIGH) == Decimal("0.5")
    assert compute_multiplier(TIER_EXTREME_HIGH) == Decimal("0.0")
    assert compute_multiplier(None) == Decimal("1.0")


def test_monthly_schedule_generates_correct_dates():
    plan = DCAPlan(
        index_id=1, amount=Decimal("2000"),
        frequency="MONTHLY", day_of_period=10,
        start_date="2026-01-01", enabled=True,
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    dates = upcoming_scheduled_dates(plan, from_=date(2026, 4, 1), lookahead_days=90)
    assert date(2026, 4, 10) in dates
    assert date(2026, 5, 10) in dates
    assert date(2026, 6, 10) in dates


def test_weekly_schedule_returns_target_weekday():
    plan = DCAPlan(
        index_id=1, amount=Decimal("500"),
        frequency="WEEKLY", day_of_period=3,  # 周三
        start_date="2026-01-01", enabled=True,
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    dates = upcoming_scheduled_dates(plan, from_=date(2026, 5, 1), lookahead_days=21)
    assert all(d.weekday() == 2 for d in dates), [d.isoformat() for d in dates]
    assert len(dates) >= 2


@pytest.fixture
def setup_for_dca(session):
    m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.flush()
    idx = IndexMeta(
        code="000300.SH", name="沪深300", market_id=m.id,
        category="宽基", data_source="fake",
        history_start_date="2015-01-01", enabled=True,
    )
    session.add(idx); session.flush()
    today = date.today()
    for i in range(0, 365 * 6, 7):
        session.add(IndexQuote(
            index_id=idx.id, date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("3500"), pe_ttm=Decimal("12"),
            source="fake", created_at=now_iso(),
        ))
    # 当前估值 → 低估（multiplier 2.0）
    session.add(Valuation(
        index_id=idx.id, date=today.isoformat(), window="10y",
        pe_percentile=Decimal("0.20"), temperature=Decimal("20.0"),
        tier="低估", computed_at=now_iso(),
    ))
    session.commit()
    return m, idx


def test_refresh_executions_uses_current_tier_for_multiplier(session, setup_for_dca):
    m, idx = setup_for_dca
    plan = DCAPlan(
        index_id=idx.id, amount=Decimal("2000"),
        frequency="WEEKLY", day_of_period=3,
        start_date=date.today().isoformat(), enabled=True,
        created_at=now_iso(), updated_at=now_iso(),
    )
    session.add(plan); session.flush()
    n = refresh_executions_for_plan(session, plan, today=date.today())
    session.commit()
    assert n >= 1
    e = session.query(DCAExecution).first()
    assert e.tier_at_decision == "低估"
    assert e.multiplier == Decimal("2.0")
    assert e.adjusted_amount == Decimal("4000.00")  # 2000 × 2.0


def test_d6_link_user_override_changes_multiplier(session, setup_for_dca):
    """D6 联动方案 A：分位 0.20 在默认下"低估"(加倍)，覆盖 low_upper=0.10 后是"合理"(正常)。"""
    m, idx = setup_for_dca
    session.add(ThresholdOverride(
        index_id=idx.id,
        boundaries_json=json.dumps({"low_upper": "0.10"}),
        updated_at=now_iso(),
    ))
    plan = DCAPlan(
        index_id=idx.id, amount=Decimal("2000"),
        frequency="WEEKLY", day_of_period=3,
        start_date=date.today().isoformat(), enabled=True,
        created_at=now_iso(), updated_at=now_iso(),
    )
    session.add(plan); session.flush()
    refresh_executions_for_plan(session, plan, today=date.today())
    session.commit()
    e = session.query(DCAExecution).first()
    assert e.tier_at_decision == "合理"
    assert e.multiplier == Decimal("1.0")
    assert e.adjusted_amount == Decimal("2000.00")


def test_actual_date_skips_non_trading_day(session, setup_for_dca):
    """SRS D6 非交易日顺延：定投日落在非交易日 → actual_date 顺延到下一开盘。"""
    m, idx = setup_for_dca
    # seed 交易日历：周一到周五开盘，周末关闭
    today = date.today()
    for i in range(60):
        d = today + timedelta(days=i)
        session.add(TradingCalendar(
            market_id=m.id, date=d.isoformat(), is_open=(d.weekday() < 5),
        ))

    # 找一个未来的周日作为定投日
    sunday = today
    while sunday.weekday() != 6 or sunday <= today:
        sunday = sunday + timedelta(days=1)

    plan = DCAPlan(
        index_id=idx.id, amount=Decimal("1000"),
        frequency="WEEKLY", day_of_period=7,  # 周日
        start_date=date.today().isoformat(), enabled=True,
        created_at=now_iso(), updated_at=now_iso(),
    )
    session.add(plan); session.flush()
    refresh_executions_for_plan(session, plan, today=date.today())
    session.commit()

    execs = session.query(DCAExecution).all()
    assert len(execs) >= 1
    for e in execs:
        sd = date.fromisoformat(e.scheduled_date)
        ad = date.fromisoformat(e.actual_date)
        assert sd.weekday() == 6, f"scheduled should be Sunday: {sd}"
        assert ad.weekday() == 0, f"actual should be Monday after skip: {ad}"
