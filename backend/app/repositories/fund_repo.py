"""SRS R12 §11.3 M7-B：Fund / FundNAV / FundValuation 仓储。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fund, FundNAV, FundValuation
from app.utils.time_utils import now_iso


# ============ Fund ============
def get_by_code(session: Session, code: str) -> Fund | None:
    return session.scalar(select(Fund).where(Fund.code == code))


def list_funds(
    session: Session, *, fund_type: str | None = None, enabled_only: bool = True,
) -> list[Fund]:
    stmt = select(Fund)
    if enabled_only:
        stmt = stmt.where(Fund.enabled == True)  # noqa: E712
    if fund_type:
        stmt = stmt.where(Fund.fund_type == fund_type)
    return list(session.scalars(stmt.order_by(Fund.market_id, Fund.code)))


def add_active_fund(
    session: Session, *,
    code: str, name: str, market_id: int,
    setup_date: str | None, fund_manager: str | None,
    fund_type_raw: str | None,
) -> Fund:
    """新增场外主动基金（无跟踪指数）。"""
    f = Fund(
        code=code, name=name, type="OPEN_FUND", fund_type="ACTIVE_FUND",
        tracks_index_id=None, market_id=market_id,
        fee_rate=None, tracking_error_note=fund_type_raw,
        setup_date=setup_date, fund_manager=fund_manager, enabled=True,
    )
    session.add(f)
    session.flush()
    return f


def delete_fund(session: Session, fund_id: int) -> bool:
    f = session.get(Fund, fund_id)
    if f is None:
        return False
    session.delete(f)
    return True


# ============ FundNAV ============
def upsert_nav(session: Session, fund_id: int, date_: str, nav: Decimal,
               accumulated_nav: Decimal | None = None) -> bool:
    existing = session.scalar(
        select(FundNAV).where(FundNAV.fund_id == fund_id, FundNAV.date == date_)
    )
    if existing is None:
        session.add(FundNAV(
            fund_id=fund_id, date=date_, nav=nav,
            accumulated_nav=accumulated_nav, created_at=now_iso(),
        ))
        return True
    changed = False
    if existing.nav != nav:
        existing.nav = nav
        changed = True
    if accumulated_nav is not None and existing.accumulated_nav != accumulated_nav:
        existing.accumulated_nav = accumulated_nav
        changed = True
    return changed


def get_nav_series(
    session: Session, fund_id: int,
    start: str | None = None, end: str | None = None,
) -> list[Decimal]:
    stmt = select(FundNAV.nav).where(FundNAV.fund_id == fund_id)
    if start:
        stmt = stmt.where(FundNAV.date >= start)
    if end:
        stmt = stmt.where(FundNAV.date <= end)
    return list(session.scalars(stmt))


def get_nav(session: Session, fund_id: int, date_: str) -> FundNAV | None:
    return session.scalar(
        select(FundNAV).where(FundNAV.fund_id == fund_id, FundNAV.date == date_)
    )


def list_recent_nav(session: Session, fund_id: int, limit: int) -> list[FundNAV]:
    return list(session.scalars(
        select(FundNAV).where(FundNAV.fund_id == fund_id)
        .order_by(FundNAV.date.desc()).limit(limit)
    ))


def list_all_nav(session: Session, fund_id: int) -> list[FundNAV]:
    return list(session.scalars(
        select(FundNAV).where(FundNAV.fund_id == fund_id).order_by(FundNAV.date.asc())
    ))


def actual_history_years(session: Session, fund_id: int) -> float:
    from datetime import date as _date
    from sqlalchemy import func

    row = session.scalar(
        select(func.min(FundNAV.date)).where(FundNAV.fund_id == fund_id)
    )
    if row is None:
        return 0.0
    return (_date.today() - _date.fromisoformat(row)).days / 365.25


# ============ FundValuation ============
def upsert_fund_valuation(session: Session, v: FundValuation) -> bool:
    existing = session.scalar(
        select(FundValuation).where(
            FundValuation.fund_id == v.fund_id,
            FundValuation.date == v.date,
            FundValuation.window == v.window,
        )
    )
    if existing is None:
        v.computed_at = now_iso()
        session.add(v)
        return True
    existing.nav_percentile = v.nav_percentile
    existing.temperature = v.temperature
    existing.tier = v.tier
    existing.computed_at = now_iso()
    return False


def latest_fund_valuation(
    session: Session, fund_id: int, window: str = "5y",
) -> FundValuation | None:
    return session.scalar(
        select(FundValuation)
        .where(FundValuation.fund_id == fund_id, FundValuation.window == window)
        .order_by(FundValuation.date.desc()).limit(1)
    )


def fund_valuation_series(
    session: Session, fund_id: int, window: str = "5y",
) -> list[FundValuation]:
    return list(session.scalars(
        select(FundValuation)
        .where(FundValuation.fund_id == fund_id, FundValuation.window == window)
        .order_by(FundValuation.date.asc())
    ))
