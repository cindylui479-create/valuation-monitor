"""SRS v1.2.0 S#3 改进：跨实体搜索（autocomplete 用）。

GET /api/v1/search?q=xxx&types=INDEX,STOCK,FUND&limit=20

返回结构：[{entity_type, code, name, market}]。
匹配规则：code 前缀（不区分大小写）OR name 子串。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Fund, IndexMeta, Market, Stock

router = APIRouter()


class SearchHit(BaseModel):
    entity_type: str    # INDEX / STOCK / FUND
    code: str
    name: str
    market: str | None
    extra: str | None = None  # 行业、类型等附加信息


class SearchResponse(BaseModel):
    items: list[SearchHit]


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, max_length=32),
    types: str = Query(default="INDEX,STOCK,FUND"),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(db_session),
) -> SearchResponse:
    q_lower = q.strip().lower()
    type_set = {t.strip().upper() for t in types.split(",") if t.strip()}
    market_by_id = {m.id: m.code for m in session.scalars(select(Market))}

    items: list[SearchHit] = []

    # INDEX
    if "INDEX" in type_set:
        idx_rows = list(session.scalars(
            select(IndexMeta)
            .where(or_(
                IndexMeta.code.ilike(f"{q_lower}%"),
                IndexMeta.name.like(f"%{q}%"),
            ))
            .order_by(IndexMeta.code)
            .limit(limit)
        ))
        for idx in idx_rows:
            items.append(SearchHit(
                entity_type="INDEX", code=idx.code, name=idx.name,
                market=market_by_id.get(idx.market_id),
                extra=idx.category,
            ))

    # STOCK（仅自选）
    if "STOCK" in type_set:
        stock_rows = list(session.scalars(
            select(Stock)
            .where(or_(
                Stock.code.ilike(f"{q_lower}%"),
                Stock.name.like(f"%{q}%"),
            ))
            .order_by(Stock.code)
            .limit(limit)
        ))
        for s in stock_rows:
            items.append(SearchHit(
                entity_type="STOCK", code=s.code, name=s.name,
                market=market_by_id.get(s.market_id),
                extra=s.industry_raw,
            ))

    # FUND
    if "FUND" in type_set:
        fund_rows = list(session.scalars(
            select(Fund)
            .where(or_(
                Fund.code.ilike(f"{q_lower}%"),
                Fund.name.like(f"%{q}%"),
            ))
            .order_by(Fund.code)
            .limit(limit)
        ))
        for f in fund_rows:
            extra = f.fund_type
            if f.fund_manager:
                extra = f"{extra} · {f.fund_manager}"
            items.append(SearchHit(
                entity_type="FUND", code=f.code, name=f.name,
                market=market_by_id.get(f.market_id),
                extra=extra,
            ))

    return SearchResponse(items=items[:limit])
