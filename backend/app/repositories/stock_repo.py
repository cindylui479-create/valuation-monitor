"""SRS R12 §11.2.1：Stock / StockQuote / StockValuation 仓储。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Stock, StockOverride, StockQuote, StockValuation
from app.utils.time_utils import now_iso


# ============ Stock ============
def get_by_code(session: Session, code: str) -> Stock | None:
    return session.scalar(select(Stock).where(Stock.code == code))


def list_stocks(session: Session, *, enabled_only: bool = True) -> list[Stock]:
    stmt = select(Stock)
    if enabled_only:
        stmt = stmt.where(Stock.enabled == True)  # noqa: E712
    return list(session.scalars(stmt.order_by(Stock.code)))


def add_stock(
    session: Session,
    *,
    code: str,
    name: str,
    market_id: int,
    industry_raw: str | None,
    listing_date: str | None,
    valuation_anchor: str = "PE",
) -> Stock:
    s = Stock(
        code=code, name=name, market_id=market_id,
        industry_raw=industry_raw, listing_date=listing_date,
        valuation_anchor=valuation_anchor,
        status="active", enabled=True,
        added_at=now_iso(),
    )
    session.add(s)
    session.flush()
    return s


def delete_stock(session: Session, stock_id: int) -> bool:
    s = session.get(Stock, stock_id)
    if s is None:
        return False
    session.delete(s)
    return True


# ============ StockQuote ============
def upsert_quote(
    session: Session, stock_id: int, row, source: str,
) -> bool:
    """row: StockQuoteRow（来自 adapter）。返回是否新增/变更。"""
    existing = session.scalar(
        select(StockQuote).where(
            StockQuote.stock_id == stock_id, StockQuote.date == row.date
        )
    )
    if existing is None:
        session.add(StockQuote(
            stock_id=stock_id, date=row.date, close=row.close,
            pe_ttm=row.pe_ttm, pe=row.pe, pb=row.pb,
            ps_ttm=row.ps_ttm, ps=row.ps,
            dividend_yield=row.dividend_yield, dv_ttm=row.dv_ttm,
            total_mv=row.total_mv, circ_mv=row.circ_mv, total_share=row.total_share,
            source=source, created_at=now_iso(),
        ))
        return True

    changed = False
    for field in ("close", "pe_ttm", "pe", "pb", "ps_ttm", "ps",
                  "dividend_yield", "dv_ttm", "total_mv", "circ_mv", "total_share"):
        old_val = getattr(existing, field)
        new_val = getattr(row, field)
        if _decimal_neq(old_val, new_val):
            setattr(existing, field, new_val)
            changed = True
    if changed:
        existing.source = source
    return changed


def get_series_for_field(
    session: Session, stock_id: int, field: str,
    start: str | None = None, end: str | None = None,
) -> list[Decimal]:
    stmt = select(getattr(StockQuote, field)).where(StockQuote.stock_id == stock_id)
    if start:
        stmt = stmt.where(StockQuote.date >= start)
    if end:
        stmt = stmt.where(StockQuote.date <= end)
    return [v for v in session.scalars(stmt) if v is not None]


def get_quote(session: Session, stock_id: int, date_: str) -> StockQuote | None:
    return session.scalar(
        select(StockQuote).where(StockQuote.stock_id == stock_id, StockQuote.date == date_)
    )


def list_recent_quotes(session: Session, stock_id: int, limit: int) -> list[StockQuote]:
    return list(session.scalars(
        select(StockQuote).where(StockQuote.stock_id == stock_id)
        .order_by(StockQuote.date.desc()).limit(limit)
    ))


def actual_history_years(session: Session, stock_id: int) -> float:
    """以 stock_quote 实际可用日期范围为准。"""
    from datetime import date as _date
    from sqlalchemy import func

    row = session.scalar(
        select(func.min(StockQuote.date)).where(StockQuote.stock_id == stock_id)
    )
    if row is None:
        return 0.0
    return (_date.today() - _date.fromisoformat(row)).days / 365.25


# ============ StockValuation ============
def upsert_valuation(session: Session, v: StockValuation) -> bool:
    existing = session.scalar(
        select(StockValuation).where(
            StockValuation.stock_id == v.stock_id,
            StockValuation.date == v.date,
            StockValuation.window == v.window,
            StockValuation.source == v.source,
        )
    )
    if existing is None:
        v.computed_at = now_iso()
        session.add(v)
        return True
    existing.anchor = v.anchor
    existing.pe_percentile = v.pe_percentile
    existing.pb_percentile = v.pb_percentile
    existing.ps_percentile = v.ps_percentile
    existing.dy_percentile = v.dy_percentile
    existing.temperature = v.temperature
    existing.tier = v.tier
    existing.computed_at = now_iso()
    return False


def latest_valuation(
    session: Session, stock_id: int, window: str = "10y",
) -> StockValuation | None:
    return session.scalar(
        select(StockValuation)
        .where(StockValuation.stock_id == stock_id, StockValuation.window == window)
        .order_by(StockValuation.date.desc()).limit(1)
    )


def valuation_series(
    session: Session, stock_id: int, window: str = "10y",
) -> list[StockValuation]:
    return list(session.scalars(
        select(StockValuation)
        .where(StockValuation.stock_id == stock_id, StockValuation.window == window)
        .order_by(StockValuation.date.asc())
    ))


# ============ StockOverride ============
def get_override(session: Session, stock_id: int) -> StockOverride | None:
    return session.scalar(select(StockOverride).where(StockOverride.stock_id == stock_id))


def upsert_override(
    session: Session, stock_id: int, *,
    valuation_anchor: str | None = None, boundaries_json: str | None = None,
) -> StockOverride:
    existing = get_override(session, stock_id)
    if existing is None:
        existing = StockOverride(
            stock_id=stock_id,
            valuation_anchor=valuation_anchor,
            boundaries_json=boundaries_json,
            updated_at=now_iso(),
        )
        session.add(existing)
    else:
        existing.valuation_anchor = valuation_anchor
        existing.boundaries_json = boundaries_json
        existing.updated_at = now_iso()
    return existing


def _decimal_neq(a, b) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return a != b
