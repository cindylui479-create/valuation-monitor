from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import IndexMeta, Watchlist


def list_all(session: Session) -> list[tuple[Watchlist, IndexMeta]]:
    rows = session.execute(
        select(Watchlist, IndexMeta).join(IndexMeta, IndexMeta.id == Watchlist.index_id)
    ).all()
    return [(r[0], r[1]) for r in rows]


def get_for_index(session: Session, index_id: int, tag: str | None = None) -> Watchlist | None:
    return session.scalar(
        select(Watchlist).where(Watchlist.index_id == index_id, Watchlist.tag == tag)
    )


def add(session: Session, index_id: int, tag: str | None, added_at: str) -> Watchlist:
    w = Watchlist(index_id=index_id, tag=tag, added_at=added_at)
    session.add(w)
    session.flush()
    return w


def delete_by_id(session: Session, watchlist_id: int) -> bool:
    w = session.get(Watchlist, watchlist_id)
    if w is None:
        return False
    session.delete(w)
    return True
