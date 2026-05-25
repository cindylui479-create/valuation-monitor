"""SRS v1.1.0 方案 A：成分股聚合 PE 单测。

公式（整体法，剔除亏损）：PE = Σmv / Σ(mv/pe)
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import (
    IndexConstituent,
    IndexConstituentQuote,
    IndexMeta,
    Market,
)
from app.services.constituent_pe_service import aggregate_pe_for_date


@pytest.fixture
def a_market(session):
    m = Market(code="A", name="A股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.commit()
    return m


@pytest.fixture
def cs_consumer(session, a_market):
    idx = IndexMeta(
        code="000932.SH", name="中证消费", market_id=a_market.id,
        category="行业", data_source="tushare",
        history_start_date="2010-01-01", enabled=True,
    )
    session.add(idx); session.commit()
    return idx


def _add_constituent(session, idx, d, code, weight):
    session.add(IndexConstituent(
        index_id=idx.id, date=d, stock_code=code,
        weight=Decimal(str(weight)), created_at="2026-05-25T00:00:00Z",
    ))


def _add_quote(session, code, d, mv, pe, pb=None):
    session.add(IndexConstituentQuote(
        stock_code=code, date=d,
        total_mv=Decimal(str(mv)) if mv is not None else None,
        pe_ttm=Decimal(str(pe)) if pe is not None else None,
        pb=Decimal(str(pb)) if pb is not None else None,
        source="tushare", created_at="2026-05-25T00:00:00Z",
    ))


def test_integrated_pe_simple(session, cs_consumer):
    """3 只成分股，整体法：PE = (100+200+300) / (100/10 + 200/20 + 300/15) = 600/40 = 15。"""
    d = "2026-05-22"
    _add_constituent(session, cs_consumer, "2026-04-30", "600001.SH", 33)
    _add_constituent(session, cs_consumer, "2026-04-30", "600002.SH", 33)
    _add_constituent(session, cs_consumer, "2026-04-30", "600003.SH", 34)
    _add_quote(session, "600001.SH", d, mv=100, pe=10)   # 利润 10
    _add_quote(session, "600002.SH", d, mv=200, pe=20)   # 利润 10
    _add_quote(session, "600003.SH", d, mv=300, pe=15)   # 利润 20
    session.commit()

    pe, meta = aggregate_pe_for_date(session, cs_consumer, d)
    # Σmv=600, Σprofit=10+10+20=40 → PE=15
    assert pe is not None
    assert abs(float(pe) - 15.0) < 0.001
    assert meta["n_eligible"] == 3
    assert meta["n_total"] == 3


def test_drops_negative_pe(session, cs_consumer):
    """亏损股（pe ≤ 0）应被剔除，不计入分母也不计入分子。"""
    d = "2026-05-22"
    _add_constituent(session, cs_consumer, "2026-04-30", "600001.SH", 50)
    _add_constituent(session, cs_consumer, "2026-04-30", "600002.SH", 50)
    _add_quote(session, "600001.SH", d, mv=100, pe=10)
    _add_quote(session, "600002.SH", d, mv=200, pe=-5)   # 亏损
    session.commit()

    pe, meta = aggregate_pe_for_date(session, cs_consumer, d)
    # 仅剩 600001：PE = 100/(100/10) = 10
    assert pe is not None
    assert abs(float(pe) - 10.0) < 0.001
    assert meta["n_eligible"] == 1
    assert meta["n_dropped_negative_pe"] == 1


def test_forward_fill_weights(session, cs_consumer):
    """月度权重应 forward-fill：报告 2026-04-30，2026-05-15 应该用 04-30 的成分股。"""
    _add_constituent(session, cs_consumer, "2026-04-30", "600001.SH", 100)
    _add_quote(session, "600001.SH", "2026-05-15", mv=1000, pe=20)
    session.commit()

    pe, meta = aggregate_pe_for_date(session, cs_consumer, "2026-05-15")
    assert pe is not None
    assert abs(float(pe) - 20.0) < 0.001
    assert meta["n_total"] == 1


def test_no_constituents_returns_none(session, cs_consumer):
    pe, meta = aggregate_pe_for_date(session, cs_consumer, "2010-01-01")
    assert pe is None
    assert meta["reason"] == "no_constituents"


def test_all_dropped_returns_none(session, cs_consumer):
    """成分股都没有 quote 数据 → 返回 None。"""
    _add_constituent(session, cs_consumer, "2026-04-30", "600001.SH", 100)
    session.commit()
    pe, meta = aggregate_pe_for_date(session, cs_consumer, "2026-05-22")
    assert pe is None
    assert meta["reason"] == "no_eligible_quotes"
    assert meta["n_dropped_no_quote"] == 1
