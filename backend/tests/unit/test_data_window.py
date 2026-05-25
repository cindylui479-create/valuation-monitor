"""SRS 附录 B R3：window 判定改用 index_quote 实际覆盖。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import IndexMeta, IndexQuote, Market
from app.services.valuation_service import (
    actual_history_years,
    data_window_note,
    has_enough_history,
)


@pytest.fixture
def index_with_quotes(session):
    m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
    session.add(m)
    session.flush()
    idx = IndexMeta(
        code="000300.SH",
        name="沪深300",
        market_id=m.id,
        category="宽基",
        data_source="fake",
        history_start_date="2005-04-08",  # YAML 理论值
        enabled=True,
    )
    session.add(idx)
    session.commit()
    return idx


def _add_quote(session, idx_id, d: date, pe: float = 12.0) -> None:
    session.add(
        IndexQuote(
            index_id=idx_id,
            date=d.isoformat(),
            close=Decimal("3000"),
            pe_ttm=Decimal(str(pe)),
            source="fake",
            created_at="2026-05-12T00:00:00Z",
        )
    )


def test_no_quotes_returns_zero_years(session, index_with_quotes):
    assert actual_history_years(session, index_with_quotes) == 0.0


def test_actual_years_uses_min_date_from_quotes(session, index_with_quotes):
    today = date.today()
    _add_quote(session, index_with_quotes.id, today - timedelta(days=365 * 2))
    _add_quote(session, index_with_quotes.id, today)
    session.commit()
    y = actual_history_years(session, index_with_quotes)
    assert 1.9 < y < 2.1


def test_data_window_note_lt_5y_returns_warning(session, index_with_quotes):
    today = date.today()
    _add_quote(session, index_with_quotes.id, today - timedelta(days=365))
    session.commit()
    assert data_window_note(session, index_with_quotes) == "分位不可用（数据 < 5 年）"


def test_data_window_note_between_5_and_10(session, index_with_quotes):
    today = date.today()
    _add_quote(session, index_with_quotes.id, today - timedelta(days=365 * 7))
    session.commit()
    note = data_window_note(session, index_with_quotes)
    assert note is not None and note.startswith("窗口=")


def test_data_window_note_ge_10y_no_note(session, index_with_quotes):
    today = date.today()
    _add_quote(session, index_with_quotes.id, today - timedelta(days=365 * 12))
    session.commit()
    assert data_window_note(session, index_with_quotes) is None


def test_has_enough_history_uses_actual_not_yaml(session, index_with_quotes):
    """关键回归：YAML 写 2005-04-08（>20 年）但 quotes 只有 1 年 → 应返回 False。"""
    today = date.today()
    _add_quote(session, index_with_quotes.id, today - timedelta(days=365))
    session.commit()
    assert has_enough_history(session, index_with_quotes) is False
