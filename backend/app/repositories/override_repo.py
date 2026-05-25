from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ThresholdOverride


def get_for_index(session: Session, index_id: int) -> ThresholdOverride | None:
    return session.scalar(
        select(ThresholdOverride).where(ThresholdOverride.index_id == index_id)
    )


def upsert(
    session: Session,
    index_id: int,
    boundaries: dict[str, str | None],
    updated_at: str,
) -> ThresholdOverride:
    existing = get_for_index(session, index_id)
    payload = json.dumps(
        {k: v for k, v in boundaries.items() if v is not None},
        ensure_ascii=False,
    )
    if existing is None:
        ov = ThresholdOverride(
            index_id=index_id, boundaries_json=payload, updated_at=updated_at
        )
        session.add(ov)
        session.flush()
        return ov
    existing.boundaries_json = payload
    existing.updated_at = updated_at
    return existing


def delete_for_index(session: Session, index_id: int) -> bool:
    ov = get_for_index(session, index_id)
    if ov is None:
        return False
    session.delete(ov)
    return True
