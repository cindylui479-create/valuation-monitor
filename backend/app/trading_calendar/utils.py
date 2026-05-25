"""交易日历查询工具。

调用方传入 Session，避免该模块强依赖 db.py。
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Market, TradingCalendar


def _market_id(session: Session, market_code: str) -> int:
    m = session.scalar(select(Market).where(Market.code == market_code))
    if m is None:
        raise ValueError(f"unknown market: {market_code}")
    return m.id


def is_open(session: Session, market_code: str, d: date) -> bool:
    """日历中无记录视为：周末关闭，工作日开盘（兜底）。"""
    mid = _market_id(session, market_code)
    row = session.scalar(
        select(TradingCalendar).where(
            TradingCalendar.market_id == mid,
            TradingCalendar.date == d.isoformat(),
        )
    )
    if row is not None:
        return bool(row.is_open)
    # fallback
    return d.weekday() < 5


def next_trading_day_inclusive(session: Session, market_code: str, d: date, max_lookahead: int = 30) -> date:
    cur = d
    for _ in range(max_lookahead):
        if is_open(session, market_code, cur):
            return cur
        cur += timedelta(days=1)
    raise ValueError(f"no trading day found within {max_lookahead} days from {d}")
