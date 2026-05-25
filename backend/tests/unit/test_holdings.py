"""SRS v1.2.0 S#3：持仓加权温度单测。

公式：weighted_temp = Σ (mv_i × temp_i) / Σ mv_i（仅含有温度的项）。
跳过 entity 不存在或无温度的项，coverage_pct = valued / total。
"""
from __future__ import annotations

from decimal import Decimal
from datetime import date, timedelta

import pytest

from app.api.holdings import _build_summary
from app.models import (
    Holding,
    IndexMeta,
    IndexQuote,
    Market,
    Valuation,
)


@pytest.fixture
def a_market(session):
    m = Market(code="A", name="A股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.commit()
    return m


@pytest.fixture
def idx_hs300(session, a_market):
    idx = IndexMeta(
        code="000300.SH", name="沪深300", market_id=a_market.id,
        category="宽基", data_source="akshare",
        history_start_date="2005-04-08", enabled=True,
    )
    session.add(idx); session.commit()
    return idx


@pytest.fixture
def idx_csi500(session, a_market):
    idx = IndexMeta(
        code="000905.SH", name="中证500", market_id=a_market.id,
        category="宽基", data_source="akshare",
        history_start_date="2007-01-15", enabled=True,
    )
    session.add(idx); session.commit()
    return idx


def _add_quote(session, idx, d, close, pe, pb):
    session.add(IndexQuote(
        index_id=idx.id, date=d, close=Decimal(str(close)),
        pe_ttm=Decimal(str(pe)) if pe else None,
        pb=Decimal(str(pb)) if pb else None,
        source="test", created_at="2026-05-25T00:00:00Z",
    ))


def _add_val(session, idx, d, temp, tier, source="lg"):
    session.add(Valuation(
        index_id=idx.id, date=d, window="10y", source=source,
        temperature=Decimal(str(temp)), tier=tier,
        temperature_source="pe_10y",
        computed_at="2026-05-25T00:00:00Z",
    ))


def test_weighted_temperature_two_indices(session, idx_hs300, idx_csi500):
    """50% 沪深300 (温度 80) + 50% 中证500 (温度 40) → 加权 60。"""
    today = date.today().isoformat()
    _add_quote(session, idx_hs300, today, close=4000, pe=14, pb=1.5)
    _add_quote(session, idx_csi500, today, close=6500, pe=22, pb=1.8)
    _add_val(session, idx_hs300, today, temp=80, tier="高估")
    _add_val(session, idx_csi500, today, temp=40, tier="合理")
    session.commit()

    holdings = [
        Holding(entity_type="INDEX", entity_code="000300.SH",
                market_value=Decimal("50000"), added_at="2026-05-25T00:00:00Z", updated_at="2026-05-25T00:00:00Z"),
        Holding(entity_type="INDEX", entity_code="000905.SH",
                market_value=Decimal("50000"), added_at="2026-05-25T00:00:00Z", updated_at="2026-05-25T00:00:00Z"),
    ]
    for h in holdings:
        session.add(h)
    session.commit()

    summary = _build_summary(session, holdings)
    assert float(summary.total_value) == 100000.0
    assert summary.weighted_temperature is not None
    assert abs(float(summary.weighted_temperature) - 60.0) < 0.01
    assert abs(float(summary.coverage_pct) - 100.0) < 0.01


def test_skip_missing_temperature(session, idx_hs300, idx_csi500):
    """中证500 没有温度时，仅沪深300 参与加权 → 加权温度 = 沪深300 温度。"""
    today = date.today().isoformat()
    _add_quote(session, idx_hs300, today, close=4000, pe=14, pb=1.5)
    _add_val(session, idx_hs300, today, temp=80, tier="高估")
    # 中证500：仅 quote 无 valuation
    _add_quote(session, idx_csi500, today, close=6500, pe=22, pb=1.8)
    session.commit()

    holdings = [
        Holding(entity_type="INDEX", entity_code="000300.SH",
                market_value=Decimal("30000"), added_at="x", updated_at="x"),
        Holding(entity_type="INDEX", entity_code="000905.SH",
                market_value=Decimal("70000"), added_at="x", updated_at="x"),
    ]
    for h in holdings:
        session.add(h)
    session.commit()

    summary = _build_summary(session, holdings)
    # coverage = 30000 / 100000 = 30%
    assert abs(float(summary.coverage_pct) - 30.0) < 0.01
    # weighted = 80（只算沪深300）
    assert abs(float(summary.weighted_temperature) - 80.0) < 0.01


def test_unknown_entity_skipped(session, idx_hs300):
    today = date.today().isoformat()
    _add_quote(session, idx_hs300, today, close=4000, pe=14, pb=1.5)
    _add_val(session, idx_hs300, today, temp=50, tier="合理")
    session.commit()

    holdings = [
        Holding(entity_type="INDEX", entity_code="000300.SH",
                market_value=Decimal("10000"), added_at="x", updated_at="x"),
        Holding(entity_type="STOCK", entity_code="999999.SZ",
                market_value=Decimal("5000"), added_at="x", updated_at="x"),
    ]
    for h in holdings:
        session.add(h)
    session.commit()

    summary = _build_summary(session, holdings)
    # 不存在的股票不影响有效部分
    assert abs(float(summary.weighted_temperature) - 50.0) < 0.01
    # 但 total_value 仍含 STOCK 这部分（15000）
    assert float(summary.total_value) == 15000.0
    assert abs(float(summary.coverage_pct) - (10000/15000*100)) < 0.01


def test_empty_holdings(session):
    summary = _build_summary(session, [])
    assert summary.total_value == "0"
    assert summary.weighted_temperature is None
    assert summary.tier_distribution == {}
