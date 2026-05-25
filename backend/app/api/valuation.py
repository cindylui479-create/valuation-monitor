from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import NotFound
from app.repositories import index_repo, quote_repo, valuation_repo
from app.schemas.valuation import ValuationPoint, ValuationSeriesResponse
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


@router.get("/indices/{code}/valuation", response_model=ValuationSeriesResponse)
def get_valuation_series(
    code: str,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    window: str = Query(default="10y", pattern=r"^(5y|10y|all)$"),
    session: Session = Depends(db_session),
) -> ValuationSeriesResponse:
    idx = index_repo.get_by_code(session, code)
    if idx is None:
        raise NotFound("index not found", code=code)

    rows = valuation_repo.series(session, idx.id, window=window, start=start, end=end)
    # 同时取 quote 中的 pe_ttm 作为附加字段
    pe_by_date = {
        q.date: q.pe_ttm
        for q in quote_repo.list_recent(session, idx.id, limit=10_000)
    }

    points = [
        ValuationPoint(
            date=r.date,
            pe_ttm=decimal_to_str(pe_by_date.get(r.date)),
            pe_percentile=decimal_to_str(r.pe_percentile),
            pb_percentile=decimal_to_str(r.pb_percentile),
            dy_percentile=decimal_to_str(r.dy_percentile),
            temperature=decimal_to_str(r.temperature),
            tier=r.tier,
        )
        for r in rows
    ]
    return ValuationSeriesResponse(code=code, window=window, series=points)
