from __future__ import annotations

import json
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import NotFound
from app.repositories import index_repo, override_repo
from app.schemas.override import Boundaries, ThresholdOverrideResponse
from app.utils.time_utils import now_iso
from app.valuation import DEFAULT_BOUNDARIES

router = APIRouter()


def _to_boundaries(override) -> Boundaries:
    """ThresholdOverride.boundaries_json → Pydantic Boundaries（缺失字段回退默认）。"""
    payload = json.loads(override.boundaries_json) if override else {}
    return Boundaries(
        extreme_low_upper=Decimal(payload.get("extreme_low_upper", str(DEFAULT_BOUNDARIES.extreme_low_upper))),
        low_upper=Decimal(payload.get("low_upper", str(DEFAULT_BOUNDARIES.low_upper))),
        high_lower=Decimal(payload.get("high_lower", str(DEFAULT_BOUNDARIES.high_lower))),
        extreme_high_lower=Decimal(payload.get("extreme_high_lower", str(DEFAULT_BOUNDARIES.extreme_high_lower))),
    )


@router.get("/threshold-overrides/{index_code}", response_model=ThresholdOverrideResponse)
def get_override(
    index_code: str, session: Session = Depends(db_session)
) -> ThresholdOverrideResponse:
    idx = index_repo.get_by_code(session, index_code)
    if idx is None:
        raise NotFound("index not found", code=index_code)
    ov = override_repo.get_for_index(session, idx.id)
    if ov is None:
        return ThresholdOverrideResponse(
            index_code=index_code,
            boundaries=Boundaries(
                extreme_low_upper=DEFAULT_BOUNDARIES.extreme_low_upper,
                low_upper=DEFAULT_BOUNDARIES.low_upper,
                high_lower=DEFAULT_BOUNDARIES.high_lower,
                extreme_high_lower=DEFAULT_BOUNDARIES.extreme_high_lower,
            ),
            is_default=True,
            updated_at=None,
        )
    return ThresholdOverrideResponse(
        index_code=index_code,
        boundaries=_to_boundaries(ov),
        is_default=False,
        updated_at=ov.updated_at,
    )


@router.put("/threshold-overrides/{index_code}", response_model=ThresholdOverrideResponse)
def put_override(
    index_code: str,
    body: Boundaries,
    session: Session = Depends(db_session),
) -> ThresholdOverrideResponse:
    idx = index_repo.get_by_code(session, index_code)
    if idx is None:
        raise NotFound("index not found", code=index_code)

    payload = {
        "extreme_low_upper": str(body.extreme_low_upper) if body.extreme_low_upper is not None else None,
        "low_upper": str(body.low_upper) if body.low_upper is not None else None,
        "high_lower": str(body.high_lower) if body.high_lower is not None else None,
        "extreme_high_lower": str(body.extreme_high_lower) if body.extreme_high_lower is not None else None,
    }
    ov = override_repo.upsert(session, idx.id, payload, updated_at=now_iso())
    session.commit()
    return ThresholdOverrideResponse(
        index_code=index_code,
        boundaries=_to_boundaries(ov),
        is_default=False,
        updated_at=ov.updated_at,
    )


@router.delete("/threshold-overrides/{index_code}", status_code=204)
def delete_override(index_code: str, session: Session = Depends(db_session)) -> None:
    idx = index_repo.get_by_code(session, index_code)
    if idx is None:
        raise NotFound("index not found", code=index_code)
    ok = override_repo.delete_for_index(session, idx.id)
    if not ok:
        raise NotFound("no override for this index", code=index_code)
    session.commit()
