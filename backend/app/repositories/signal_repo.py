from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DCAPlan, IndexMeta, Signal, Watchlist


def upsert(session: Session, s: Signal) -> None:
    """SRS R10：唯一键 (index_id, date, source)；存在则更新方向/温度/档位。"""
    existing = session.scalar(
        select(Signal).where(
            Signal.index_id == s.index_id,
            Signal.date == s.date,
            Signal.source == s.source,
        )
    )
    if existing is None:
        session.add(s)
        return
    existing.direction = s.direction
    existing.tier = s.tier
    existing.temperature = s.temperature
    existing.generated_at = s.generated_at


def delete_for_date(session: Session, index_id: int, date_: str, source: str = "lg") -> bool:
    s = session.scalar(
        select(Signal).where(
            Signal.index_id == index_id,
            Signal.date == date_,
            Signal.source == source,
        )
    )
    if s is None:
        return False
    session.delete(s)
    return True


def list_signals(
    session: Session,
    date_from: str | None = None,
    date_to: str | None = None,
    market_code: str | None = None,
    direction: str | None = None,
    source: str = "lg",
    only_subscribed: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list[tuple[Signal, IndexMeta]]:
    """按条件查询信号。only_subscribed=True 时仅返回出现在 Watchlist 或 DCAPlan 中的指数。

    返回 (Signal, IndexMeta) 二元组列表，按日期倒序。
    """
    stmt = (
        select(Signal, IndexMeta)
        .join(IndexMeta, IndexMeta.id == Signal.index_id)
        .where(Signal.source == source)
    )
    if date_from:
        stmt = stmt.where(Signal.date >= date_from)
    if date_to:
        stmt = stmt.where(Signal.date <= date_to)
    if direction:
        stmt = stmt.where(Signal.direction == direction)
    if market_code:
        from app.models import Market

        m = session.scalar(select(Market).where(Market.code == market_code))
        if m is None:
            return []
        stmt = stmt.where(IndexMeta.market_id == m.id)
    if only_subscribed:
        # 出现在 Watchlist 或 DCAPlan 中
        wl_ids = {x for x, in session.execute(select(Watchlist.index_id)).all()}
        dca_ids = {x for x, in session.execute(select(DCAPlan.index_id).where(DCAPlan.enabled == True)).all()}  # noqa: E712
        subscribed = list(wl_ids | dca_ids)
        if not subscribed:
            return []
        stmt = stmt.where(Signal.index_id.in_(subscribed))

    stmt = stmt.order_by(Signal.date.desc(), Signal.id.desc()).limit(limit).offset(offset)
    rows = session.execute(stmt).all()
    return [(r[0], r[1]) for r in rows]
