"""SRS R12 M6-A：个股估值计算单测。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Market, Stock, StockQuote, StockValuation
from app.services.stock_valuation_service import recompute_for_stock
from app.valuation.anchor import (
    default_anchor_for_industry,
    temperature_from_anchor,
)


@pytest.fixture
def a_market(session):
    m = Market(code="A", name="A股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.commit()
    return m


@pytest.fixture
def stock_moutai(session, a_market):
    s = Stock(
        code="600519.SH", name="贵州茅台", market_id=a_market.id,
        industry_raw="食品饮料", listing_date="2001-08-27",
        valuation_anchor="PE", status="active", enabled=True,
        added_at="2026-05-19T00:00:00Z",
    )
    session.add(s); session.commit()
    return s


@pytest.fixture
def stock_pingan(session, a_market):
    s = Stock(
        code="000001.SZ", name="平安银行", market_id=a_market.id,
        industry_raw="银行", listing_date="1991-04-03",
        valuation_anchor="PB",
        added_at="2026-05-19T00:00:00Z",
    )
    session.add(s); session.commit()
    return s


def _add_quotes_synthetic(session, stock, n=260, pe_start=Decimal("20")):
    today = date.today()
    for i in range(n):
        d = (today - timedelta(days=n - 1 - i)).isoformat()
        session.add(StockQuote(
            stock_id=stock.id, date=d, close=Decimal("100"),
            pe_ttm=pe_start + Decimal(i % 10),
            pb=Decimal("1.5") + Decimal(i % 5) / Decimal(10),
            ps_ttm=Decimal("5") + Decimal(i % 3),
            dv_ttm=Decimal("0.02") + Decimal(i % 4) / Decimal(1000),
            source="test", created_at="2026-05-19T00:00:00Z",
        ))
    session.commit()


# ============ 行业映射 ============
def test_anchor_mapping():
    assert default_anchor_for_industry("银行") == "PB"
    assert default_anchor_for_industry("食品饮料") == "PE"
    assert default_anchor_for_industry("钢铁") == "PE_REVERSE"
    assert default_anchor_for_industry("计算机") == "PS"
    assert default_anchor_for_industry("公用事业") == "DIV_YIELD"
    assert default_anchor_for_industry(None) == "PE"
    assert default_anchor_for_industry("某未知行业 XYZ") == "PE"


# ============ 温度公式 ============
def test_temperature_pe():
    t = temperature_from_anchor("PE", pe_pctl=Decimal("0.75"), pb_pctl=None, ps_pctl=None, dy_pctl=None)
    assert t == Decimal("75.00")


def test_temperature_pb():
    t = temperature_from_anchor("PB", pe_pctl=None, pb_pctl=Decimal("0.30"), ps_pctl=None, dy_pctl=None)
    assert t == Decimal("30.00")


def test_temperature_pe_reverse():
    # PE 高位（90%）→ 温度低（10）：周期股 PE 倒置
    t = temperature_from_anchor("PE_REVERSE", pe_pctl=Decimal("0.9"), pb_pctl=None, ps_pctl=None, dy_pctl=None)
    assert t == Decimal("10.0")


def test_temperature_div_yield_reverse():
    # 股息率高（90%）→ 温度低（10）：股息率倒置
    t = temperature_from_anchor("DIV_YIELD", pe_pctl=None, pb_pctl=None, ps_pctl=None, dy_pctl=Decimal("0.9"))
    assert t == Decimal("10.0")


def test_temperature_missing_anchor_field():
    # PE 锚但 pe_pctl 缺失
    t = temperature_from_anchor("PE", pe_pctl=None, pb_pctl=Decimal("0.5"), ps_pctl=None, dy_pctl=None)
    assert t is None


# ============ recompute_for_stock ============
def test_recompute_writes_valuation_with_temperature(session, stock_moutai):
    _add_quotes_synthetic(session, stock_moutai, n=260)
    today = date.today().isoformat()
    written = recompute_for_stock(session, stock_moutai, [today])

    assert written == 3  # 3 个 window
    v_10y = session.query(StockValuation).filter_by(
        stock_id=stock_moutai.id, date=today, window="10y"
    ).one()
    assert v_10y.pe_percentile is not None
    assert v_10y.temperature is not None
    assert v_10y.anchor == "PE"
    assert v_10y.tier is not None


def test_recompute_bank_uses_pb_anchor(session, stock_pingan):
    """平安银行 anchor=PB，温度公式应用 PB 百分位。"""
    _add_quotes_synthetic(session, stock_pingan, n=260)
    today = date.today().isoformat()
    recompute_for_stock(session, stock_pingan, [today])

    v_10y = session.query(StockValuation).filter_by(
        stock_id=stock_pingan.id, date=today, window="10y"
    ).one()
    assert v_10y.anchor == "PB"
    # 温度应该约等于 pb_percentile × 100
    expected = v_10y.pb_percentile * Decimal(100)
    assert abs(v_10y.temperature - expected) < Decimal("0.01")
