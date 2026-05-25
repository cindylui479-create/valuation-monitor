"""SignalEngine 单元 + 集成测试（M4）。"""
from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import IndexMeta, IndexQuote, Market, Signal, ThresholdOverride, Valuation
from app.services.signal_engine import generate_signals_for
from app.utils.time_utils import now_iso


@pytest.fixture
def setup_index(session):
    m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.flush()
    idx = IndexMeta(
        code="000300.SH", name="沪深300", market_id=m.id,
        category="宽基", data_source="fake",
        history_start_date="2015-01-01", enabled=True,
    )
    session.add(idx)
    # 历史 quotes >= 5 年（has_enough_history 通过）
    today = date.today()
    for i in range(0, 365 * 6, 7):
        session.add(IndexQuote(
            index_id=1, date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("3500"), pe_ttm=Decimal("12"),
            source="fake", created_at=now_iso(),
        ))
    session.commit()
    return idx


def _add_latest_valuation(session, idx_id: int, pe_percentile: Decimal, target: date | None = None):
    target = target or date.today()
    from decimal import Decimal as D
    session.add(Valuation(
        index_id=idx_id, date=target.isoformat(), window="10y",
        pe_percentile=pe_percentile,
        temperature=pe_percentile * D(100),
        tier=None,
        computed_at=now_iso(),
    ))
    session.commit()


def test_extreme_low_produces_strong_buy(session, setup_index):
    _add_latest_valuation(session, setup_index.id, Decimal("0.05"))  # 5% 极度低估
    n = generate_signals_for(session, "A", date.today().isoformat())
    assert n == 1
    s = session.query(Signal).one()
    assert s.direction == "STRONG_BUY"
    assert s.tier == "极度低估"


def test_fair_does_not_produce_signal(session, setup_index):
    _add_latest_valuation(session, setup_index.id, Decimal("0.50"))
    n = generate_signals_for(session, "A", date.today().isoformat())
    assert n == 0
    assert session.query(Signal).count() == 0


def test_extreme_high_produces_strong_sell(session, setup_index):
    _add_latest_valuation(session, setup_index.id, Decimal("0.95"))
    n = generate_signals_for(session, "A", date.today().isoformat())
    assert n == 1
    assert session.query(Signal).one().direction == "STRONG_SELL"


def test_d6_link_a_user_overrides_widens_buy_range(session, setup_index):
    """D6 联动方案 A：用户把"低估上限"调到 15%，分位 0.12 → 仍是"低估"，触发 BUY。
    默认情况下 0.12 在 10~30% → "低估" → BUY；将 low_upper 调至 10% 后变"合理" → 无信号。"""
    # 默认情况：分位 0.12，应是低估
    _add_latest_valuation(session, setup_index.id, Decimal("0.12"))
    generate_signals_for(session, "A", date.today().isoformat())
    assert session.query(Signal).one().direction == "BUY"
    session.query(Signal).delete()

    # 覆盖：把低估上限调成 0.10
    session.add(ThresholdOverride(
        index_id=setup_index.id,
        boundaries_json=json.dumps({"low_upper": "0.10"}),
        updated_at=now_iso(),
    ))
    session.commit()
    generate_signals_for(session, "A", date.today().isoformat())
    assert session.query(Signal).count() == 0  # 0.12 在覆盖后已是"合理"


def test_history_less_than_5y_no_signal(session):
    m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
    session.add(m); session.flush()
    idx = IndexMeta(code="000688.SH", name="科创50", market_id=m.id,
                    category="宽基", data_source="fake",
                    history_start_date="2024-01-01", enabled=True)
    session.add(idx); session.flush()
    # quotes 仅 1 年
    today = date.today()
    for i in range(0, 365, 7):
        session.add(IndexQuote(
            index_id=idx.id, date=(today - timedelta(days=i)).isoformat(),
            close=Decimal("1000"), pe_ttm=Decimal("100"),
            source="fake", created_at=now_iso(),
        ))
    session.commit()
    _add_latest_valuation(session, idx.id, Decimal("0.05"))
    n = generate_signals_for(session, "A", date.today().isoformat())
    assert n == 0
