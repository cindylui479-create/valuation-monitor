from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IndexQuote
from app.utils.time_utils import now_iso


def upsert_quote(session: Session, q: IndexQuote, source: str) -> tuple[bool, list[tuple[str, str | None, str | None]]]:
    """插入或更新单条记录。返回 (is_changed, [(field, old, new), ...])。

    供 data_pipeline 写审计日志使用。
    """
    existing = session.scalar(
        select(IndexQuote).where(
            IndexQuote.index_id == q.index_id, IndexQuote.date == q.date
        )
    )
    if existing is None:
        q.source = source
        q.created_at = now_iso()
        session.add(q)
        return True, []

    diffs: list[tuple[str, str | None, str | None]] = []
    for field in (
        "close",
        "pe_ttm",
        "pb",
        "dividend_yield",
        "roe",
        "earnings_growth_3y",
        "ma50",
        "ma200",
        "northbound_60d_pct",
    ):
        old_val = getattr(existing, field)
        new_val = getattr(q, field)
        if _decimal_neq(old_val, new_val):
            diffs.append((field, _to_s(old_val), _to_s(new_val)))
            setattr(existing, field, new_val)
    if diffs:
        existing.source = source
    return bool(diffs), diffs


def get_series_for_field(
    session: Session,
    index_id: int,
    field: str,
    start: str | None = None,
    end: str | None = None,
) -> list[Decimal]:
    stmt = select(getattr(IndexQuote, field)).where(IndexQuote.index_id == index_id)
    if start:
        stmt = stmt.where(IndexQuote.date >= start)
    if end:
        stmt = stmt.where(IndexQuote.date <= end)
    return [v for v in session.scalars(stmt) if v is not None]


def get_quote(session: Session, index_id: int, date_: str) -> IndexQuote | None:
    return session.scalar(
        select(IndexQuote).where(IndexQuote.index_id == index_id, IndexQuote.date == date_)
    )


def update_csi_values(
    session: Session, index_id: int, date_: str,
    pe_ttm_csi: Decimal | None, pb_csi: Decimal | None,
) -> bool:
    """SRS R10：单独更新 pe_ttm_csi / pb_csi 两列，不动其他字段。"""
    row = session.scalar(
        select(IndexQuote).where(IndexQuote.index_id == index_id, IndexQuote.date == date_)
    )
    if row is None:
        return False
    if pe_ttm_csi is not None:
        row.pe_ttm_csi = pe_ttm_csi
    if pb_csi is not None:
        row.pb_csi = pb_csi
    return True


def list_recent(session: Session, index_id: int, limit: int) -> list[IndexQuote]:
    return list(
        session.scalars(
            select(IndexQuote)
            .where(IndexQuote.index_id == index_id)
            .order_by(IndexQuote.date.desc())
            .limit(limit)
        )
    )


def _decimal_neq(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None and b is None:
        return False
    if a is None or b is None:
        return True
    return a != b


def _to_s(v: Decimal | None) -> str | None:
    return None if v is None else format(v, "f")
