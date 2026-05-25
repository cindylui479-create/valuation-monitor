from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Valuation


def upsert_valuation(session: Session, v: Valuation) -> None:
    """SRS R10：唯一键含 source；同 (index, date, window, source) 存在则更新。"""
    existing = session.scalar(
        select(Valuation).where(
            Valuation.index_id == v.index_id,
            Valuation.date == v.date,
            Valuation.window == v.window,
            Valuation.source == v.source,
        )
    )
    if existing is None:
        session.add(v)
        return
    existing.pe_percentile = v.pe_percentile
    existing.pb_percentile = v.pb_percentile
    existing.dy_percentile = v.dy_percentile
    existing.close_percentile = v.close_percentile
    existing.temperature = v.temperature
    existing.tier = v.tier
    existing.temperature_source = v.temperature_source
    existing.computed_at = v.computed_at


def latest(
    session: Session,
    index_id: int,
    window: str = "10y",
    source: str = "lg",
) -> Valuation | None:
    """SRS R10：默认 lg；若该指数 lg 没数据但 csi 有，调用方应再试 csi。"""
    return session.scalar(
        select(Valuation)
        .where(
            Valuation.index_id == index_id,
            Valuation.window == window,
            Valuation.source == source,
        )
        .order_by(Valuation.date.desc())
        .limit(1)
    )


def latest_with_fallback(
    session: Session,
    index_id: int,
    window: str = "10y",
    preferred: str = "lg",
) -> tuple[Valuation, str] | None:
    """按偏好源取最新；若无数据则回退另一源。返回 (row, effective_source) 或 None。"""
    primary = latest(session, index_id, window, source=preferred)
    if primary is not None:
        return primary, preferred
    alt = "csi" if preferred == "lg" else "lg"
    fallback = latest(session, index_id, window, source=alt)
    if fallback is not None:
        return fallback, alt
    return None


def series(
    session: Session,
    index_id: int,
    window: str,
    source: str = "lg",
    start: str | None = None,
    end: str | None = None,
) -> list[Valuation]:
    stmt = select(Valuation).where(
        Valuation.index_id == index_id,
        Valuation.window == window,
        Valuation.source == source,
    )
    if start:
        stmt = stmt.where(Valuation.date >= start)
    if end:
        stmt = stmt.where(Valuation.date <= end)
    stmt = stmt.order_by(Valuation.date)
    return list(session.scalars(stmt))
