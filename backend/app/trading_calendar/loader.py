"""把数据源给出的日历写入 TradingCalendar 表。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Market, TradingCalendar


def upsert_calendar(session: Session, market_code: str, days: list[tuple[str, bool]]) -> int:
    """days: [(YYYY-MM-DD, is_open), ...]。返回写入/更新条数。"""
    m = session.scalar(select(Market).where(Market.code == market_code))
    if m is None:
        raise ValueError(f"unknown market: {market_code}")

    existing = {
        r.date: r
        for r in session.scalars(
            select(TradingCalendar).where(TradingCalendar.market_id == m.id)
        ).all()
    }
    n = 0
    for d, is_open in days:
        row = existing.get(d)
        if row is None:
            session.add(TradingCalendar(market_id=m.id, date=d, is_open=is_open))
            n += 1
        elif bool(row.is_open) != is_open:
            row.is_open = is_open
            n += 1
    session.flush()
    return n
