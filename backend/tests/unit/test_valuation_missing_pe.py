"""港美股 quotes 中 PE 为 None 时（M3 R7），valuation_service 应跳过分位计算。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import IndexMeta, IndexQuote, Market, Valuation
from app.services.valuation_service import recompute_for_index


@pytest.fixture
def us_index(session):
    m = Market(code="US", name="美国", currency="USD", tz="America/New_York")
    session.add(m); session.flush()
    idx = IndexMeta(
        code="SPY", name="标普500", market_id=m.id, category="宽基",
        data_source="yfinance", history_start_date="1993-01-29", enabled=True,
    )
    session.add(idx); session.commit()
    return idx


def test_skip_when_pe_missing(session, us_index):
    today = date.today()
    # 5 行 quotes 全部无 PE（典型 yfinance 历史）
    for i in range(5):
        session.add(IndexQuote(
            index_id=us_index.id,
            date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("500"),
            pe_ttm=None,  # 关键：无 PE
            pb=None,
            source="yfinance",
            created_at="2026-05-12T00:00:00Z",
        ))
    session.commit()

    dates = [(today - timedelta(days=i)).isoformat() for i in range(5)]
    written = recompute_for_index(session, us_index, dates)

    assert written == 0, "无 PE 的日期都应该被跳过，valuation 表不应有行"
    assert session.query(Valuation).count() == 0


def test_snapshot_only_pe_does_not_produce_percentile(session, us_index):
    """SRS R7：只有最新快照 PE 时序列点数 < MIN_DATAPOINTS_FOR_PERCENTILE，
    分位 / 温度 / 档位都应为 None（不能伪造 50.0 的"合理"信号）。"""
    today = date.today()
    for i in range(5):
        session.add(IndexQuote(
            index_id=us_index.id,
            date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("500"),
            pe_ttm=Decimal("27.5") if i == 0 else None,
            pb=None,
            source="yfinance",
            created_at="2026-05-12T00:00:00Z",
        ))
    session.commit()

    dates = [(today - timedelta(days=i)).isoformat() for i in range(5)]
    written = recompute_for_index(session, us_index, dates)

    # 仍然会写 3 行 valuation（3 个窗口），但分位/温度/档位都是 None
    assert written == 3
    rows = session.query(Valuation).filter_by(date=today.isoformat()).all()
    assert len(rows) == 3
    for r in rows:
        assert r.pe_percentile is None
        assert r.temperature is None
        assert r.tier is None


def test_pe_percentile_produced_when_enough_history(session, us_index):
    """≥250 个 PE 数据点时分位有效。"""
    today = date.today()
    for i in range(260):
        session.add(IndexQuote(
            index_id=us_index.id,
            date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("500"),
            pe_ttm=Decimal("20") + Decimal(i % 10),
            pb=None,
            source="yfinance",
            created_at="2026-05-12T00:00:00Z",
        ))
    session.commit()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(260)]
    recompute_for_index(session, us_index, dates)
    today_row = (
        session.query(Valuation)
        .filter_by(date=today.isoformat(), window="10y")
        .one()
    )
    assert today_row.pe_percentile is not None
    assert today_row.temperature is not None
    assert today_row.tier is not None
