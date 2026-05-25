"""SRS R12 M7-B：主动基金 NAV 历史百分位 → 温度 单测。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Fund, FundNAV, FundValuation, Market
from app.services.fund_valuation_service import recompute_for_fund
from app.adapters.fund_akshare_adapter import _is_active_fund


@pytest.fixture
def a_market(session):
    m = Market(code="A", name="A股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.commit()
    return m


@pytest.fixture
def active_fund(session, a_market):
    f = Fund(
        code="005827", name="易方达蓝筹精选混合",
        type="OPEN_FUND", fund_type="ACTIVE_FUND",
        tracks_index_id=None, market_id=a_market.id,
        setup_date="2018-09-05",
        fund_manager="张坤",
        enabled=True,
    )
    session.add(f); session.commit()
    return f


@pytest.fixture
def etf_fund(session, a_market):
    f = Fund(
        code="510300.SH", name="华泰柏瑞沪深300ETF",
        type="ETF", fund_type="ETF",
        tracks_index_id=None, market_id=a_market.id, enabled=True,
    )
    session.add(f); session.commit()
    return f


def _add_navs(session, fund, n=300, start_nav=Decimal("1.0")):
    today = date.today()
    for i in range(n):
        d = (today - timedelta(days=n - 1 - i)).isoformat()
        # 模拟波动：基础 + 周期性
        nav = start_nav + Decimal(i % 50) / Decimal(100)
        session.add(FundNAV(
            fund_id=fund.id, date=d, nav=nav,
            created_at="2026-05-19T00:00:00Z",
        ))
    session.commit()


# ============ _is_active_fund 类型识别 ============
def test_is_active_fund_mixed():
    assert _is_active_fund("混合型-偏股") is True
    assert _is_active_fund("股票型") is True
    assert _is_active_fund("债券型") is True
    assert _is_active_fund("QDII") is True


def test_is_active_fund_passive():
    assert _is_active_fund("ETF") is False
    assert _is_active_fund("股票指数") is False
    assert _is_active_fund("指数增强") is False  # 含"指数"
    assert _is_active_fund(None) is False


# ============ recompute_for_fund ============
def test_recompute_writes_valuation(session, active_fund):
    _add_navs(session, active_fund, n=300)
    today = date.today().isoformat()
    written = recompute_for_fund(session, active_fund, [today])
    assert written == 2  # 5y + all

    v_5y = session.query(FundValuation).filter_by(
        fund_id=active_fund.id, date=today, window="5y"
    ).one()
    assert v_5y.nav_percentile is not None
    assert v_5y.temperature is not None
    assert v_5y.tier is not None


def test_recompute_skips_etf(session, etf_fund):
    """ETF 基金不走 NAV 估值路径（fund_type='ETF'）。"""
    _add_navs(session, etf_fund, n=300)
    today = date.today().isoformat()
    written = recompute_for_fund(session, etf_fund, [today])
    assert written == 0
    assert session.query(FundValuation).count() == 0


def test_recompute_skips_when_history_short(session, active_fund):
    """NAV < 250 点（< 1 年）时温度应为 None（保留分位行但温度空）。"""
    _add_navs(session, active_fund, n=100)
    today = date.today().isoformat()
    written = recompute_for_fund(session, active_fund, [today])
    assert written == 2

    v_5y = session.query(FundValuation).filter_by(
        fund_id=active_fund.id, date=today, window="5y"
    ).one()
    assert v_5y.nav_percentile is None
    assert v_5y.temperature is None
