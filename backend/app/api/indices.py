from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import NotFound
from app.models import Market
from app.repositories import index_repo
from app.schemas.index import FundDTO, IndexDTO
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


@router.get("/indices", response_model=list[IndexDTO])
def list_indices(
    market: str | None = Query(default=None),
    category: str | None = Query(default=None),
    session: Session = Depends(db_session),
) -> list[IndexDTO]:
    indices = index_repo.list_indices(session, market_code=market, category=category)
    markets = {m.id: m.code for m in session.query(Market).all()}
    out: list[IndexDTO] = []
    for idx in indices:
        funds = index_repo.funds_for(session, idx.id)
        out.append(
            IndexDTO(
                code=idx.code,
                name=idx.name,
                market=markets.get(idx.market_id, ""),
                category=idx.category,
                industry_raw=idx.industry_raw,
                data_source=idx.data_source,
                history_start_date=idx.history_start_date,
                enabled=idx.enabled,
                funds=[
                    FundDTO(
                        code=f.code,
                        name=f.name,
                        type=f.type,
                        fee_rate=decimal_to_str(f.fee_rate),
                        tracking_error_note=f.tracking_error_note,
                    )
                    for f in funds
                ],
            )
        )
    return out


@router.get("/indices/{code}", response_model=IndexDTO)
def get_index(code: str, session: Session = Depends(db_session)) -> IndexDTO:
    idx = index_repo.get_by_code(session, code)
    if idx is None:
        raise NotFound("index not found", code=code)
    market = session.get(Market, idx.market_id)
    funds = index_repo.funds_for(session, idx.id)
    return IndexDTO(
        code=idx.code,
        name=idx.name,
        market=market.code if market else "",
        category=idx.category,
        industry_raw=idx.industry_raw,
        data_source=idx.data_source,
        history_start_date=idx.history_start_date,
        enabled=idx.enabled,
        funds=[
            FundDTO(
                code=f.code,
                name=f.name,
                type=f.type,
                fee_rate=decimal_to_str(f.fee_rate),
                tracking_error_note=f.tracking_error_note,
            )
            for f in funds
        ],
    )
