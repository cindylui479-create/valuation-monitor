"""User preferences API（M5）。

存在 user_preference 表，按 key 索引。值是 JSON 字符串。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import UserPreference
from app.utils.time_utils import now_iso

router = APIRouter()

DEFAULTS: dict[str, object] = {
    "default_window": "10y",
    "theme": "light",
    "overview_default_filter": "all",
    # SRS R10：PE 口径 lg / csi
    "pe_source": "lg",
}


def _get(session: Session, key: str) -> object:
    row = session.scalar(select(UserPreference).where(UserPreference.key == key))
    if row is None:
        return DEFAULTS.get(key)
    try:
        return json.loads(row.value_json)
    except Exception:
        return DEFAULTS.get(key)


def _set(session: Session, key: str, value: object) -> None:
    row = session.scalar(select(UserPreference).where(UserPreference.key == key))
    payload = json.dumps(value, ensure_ascii=False)
    if row is None:
        session.add(UserPreference(key=key, value_json=payload, updated_at=now_iso()))
    else:
        row.value_json = payload
        row.updated_at = now_iso()


@router.get("/preferences")
def get_preferences(session: Session = Depends(db_session)) -> dict:
    return {k: _get(session, k) for k in DEFAULTS}


@router.put("/preferences")
def put_preferences(
    body: dict = Body(...),
    session: Session = Depends(db_session),
) -> dict:
    for k, v in body.items():
        if k in DEFAULTS:
            _set(session, k, v)
    session.commit()
    return {k: _get(session, k) for k in DEFAULTS}
