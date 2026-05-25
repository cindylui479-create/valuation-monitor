from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Fund, IndexMeta, Market


def list_indices(
    session: Session,
    market_code: str | None = None,
    category: str | None = None,
    enabled_only: bool = True,
) -> list[IndexMeta]:
    stmt = select(IndexMeta)
    if enabled_only:
        stmt = stmt.where(IndexMeta.enabled == True)  # noqa: E712
    if market_code:
        m = session.scalar(select(Market).where(Market.code == market_code))
        if m is None:
            return []
        stmt = stmt.where(IndexMeta.market_id == m.id)
    if category:
        stmt = stmt.where(IndexMeta.category == category)
    return list(session.scalars(stmt))


def get_by_code(session: Session, code: str) -> IndexMeta | None:
    return session.scalar(select(IndexMeta).where(IndexMeta.code == code))


def funds_for(session: Session, index_id: int) -> list[Fund]:
    return list(session.scalars(select(Fund).where(Fund.tracks_index_id == index_id)))
