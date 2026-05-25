"""SRS v1.2.0 A#8：机会扫描 API。

GET /api/v1/opportunities
扫所有跟踪实体（指数 + 个股 + ACTIVE_FUND），按温度 tier 筛出值得关注的：
- 极度低估
- 低估
- 极度高估（"减仓提醒"角度）

排序：tier 严重度 + 温度。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Fund, IndexMeta, Market, Stock
from app.repositories import fund_repo, stock_repo, valuation_repo
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


_TIER_RANK = {
    "极度低estimate": -2, "极度低估": -2,
    "低估": -1,
    "合理": 0,
    "高估": 1,
    "极度高估": 2,
}


class Opportunity(BaseModel):
    entity_type: str
    entity_code: str
    entity_name: str
    market: str | None
    temperature: str
    tier: str
    temperature_source: str | None
    pe_ttm: str | None
    pb: str | None


class OpportunitiesResponse(BaseModel):
    low_valuations: list[Opportunity]    # 低估 + 极度低估
    high_valuations: list[Opportunity]   # 极度高估
    total: int


def _scan_indices(session: Session, market_by_id: dict[int, str]) -> list[Opportunity]:
    from app.repositories import quote_repo
    out = []
    for idx in session.scalars(select(IndexMeta).where(IndexMeta.enabled == True)):  # noqa: E712
        v_with_src = valuation_repo.latest_with_fallback(session, idx.id, "10y", preferred="lg")
        if not v_with_src:
            continue
        v = v_with_src[0]
        if v.tier is None or v.temperature is None:
            continue
        recent = quote_repo.list_recent(session, idx.id, limit=1)
        q = recent[0] if recent else None
        out.append(Opportunity(
            entity_type="INDEX", entity_code=idx.code, entity_name=idx.name,
            market=market_by_id.get(idx.market_id),
            temperature=decimal_to_str(v.temperature) or "0",
            tier=v.tier,
            temperature_source=v.temperature_source,
            pe_ttm=decimal_to_str(q.pe_ttm) if q else None,
            pb=decimal_to_str(q.pb) if q else None,
        ))
    return out


def _scan_stocks(session: Session, market_by_id: dict[int, str]) -> list[Opportunity]:
    out = []
    for s in stock_repo.list_stocks(session):
        v = stock_repo.latest_valuation(session, s.id)
        if v is None or v.tier is None or v.temperature is None:
            continue
        recent = stock_repo.list_recent_quotes(session, s.id, limit=1)
        q = recent[0] if recent else None
        out.append(Opportunity(
            entity_type="STOCK", entity_code=s.code, entity_name=s.name,
            market=market_by_id.get(s.market_id),
            temperature=decimal_to_str(v.temperature) or "0",
            tier=v.tier, temperature_source="pe_10y",
            pe_ttm=decimal_to_str(q.pe_ttm) if q else None,
            pb=decimal_to_str(q.pb) if q else None,
        ))
    return out


def _scan_active_funds(session: Session, market_by_id: dict[int, str]) -> list[Opportunity]:
    out = []
    funds = fund_repo.list_funds(session, fund_type="ACTIVE_FUND")
    for f in funds:
        v = fund_repo.latest_fund_valuation(session, f.id, "5y")
        if v is None or v.tier is None or v.temperature is None:
            continue
        out.append(Opportunity(
            entity_type="FUND", entity_code=f.code, entity_name=f.name,
            market=market_by_id.get(f.market_id),
            temperature=decimal_to_str(v.temperature) or "0",
            tier=v.tier, temperature_source="nav_5y",
            pe_ttm=None, pb=None,
        ))
    return out


@router.get("/opportunities", response_model=OpportunitiesResponse)
def list_opportunities(
    include_extreme_high: bool = Query(default=True),
    session: Session = Depends(db_session),
) -> OpportunitiesResponse:
    market_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    all_items: list[Opportunity] = []
    all_items += _scan_indices(session, market_by_id)
    all_items += _scan_stocks(session, market_by_id)
    all_items += _scan_active_funds(session, market_by_id)

    low = [it for it in all_items if it.tier in ("低估", "极度低估")]
    high = [it for it in all_items if it.tier == "极度高估"] if include_extreme_high else []

    # 排序：极度低估 → 低估；温度升序（更低更前）
    low.sort(key=lambda o: (
        0 if o.tier == "极度低估" else 1,
        float(o.temperature),
    ))
    # 极度高估：温度降序
    high.sort(key=lambda o: -float(o.temperature))

    return OpportunitiesResponse(
        low_valuations=low, high_valuations=high, total=len(low) + len(high),
    )
