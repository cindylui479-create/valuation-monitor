"""SRS v1.2.0 S#2：温度跳变检测（动态查询，不落表）。

GET /api/v1/tier-transitions?days=7
返回过去 N 天内所有"跨档位"事件：(entity, 日期, from_tier→to_tier, 温度变化)

适用范围：INDEX + STOCK + FUND(ACTIVE_FUND)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import (
    Fund,
    FundValuation,
    IndexMeta,
    Market,
    Stock,
    StockValuation,
    Valuation,
)
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


# 五档位的"严重度"排序 — 跨度大的跳变标 HIGH
_TIER_ORDER = {
    "极度低估": 0, "低估": 1, "合理": 2, "高估": 3, "极度高估": 4,
}


class TierTransition(BaseModel):
    entity_type: str
    entity_code: str
    entity_name: str
    date: str                      # 跳变发生日（即 to_tier 那天）
    from_tier: str | None
    to_tier: str
    from_temperature: str | None
    to_temperature: str
    temperature_delta: str
    severity: str                  # 'HIGH' (跨 2+ 档) / 'MEDIUM' (跨 1 档) / 'INFO' (温度变 ≥ 10 同档)
    direction: str                 # 'up' / 'down'


class TierTransitionsResponse(BaseModel):
    days: int
    items: list[TierTransition]


def _classify(from_tier: str | None, to_tier: str, delta: Decimal) -> tuple[str, str]:
    """返回 (severity, direction)。"""
    direction = "up" if delta > 0 else "down"
    if from_tier is None or from_tier == to_tier:
        # 同档但温度跳 ≥ 10：INFO
        return ("INFO", direction)
    span = abs(_TIER_ORDER.get(to_tier, 2) - _TIER_ORDER.get(from_tier, 2))
    if span >= 2:
        return ("HIGH", direction)
    return ("MEDIUM", direction)


def _scan_index_transitions(
    session: Session, start_date: str, market_by_id: dict[int, str],
) -> list[TierTransition]:
    """扫所有指数 valuation_series（10y / lg），找最近跳变。"""
    out: list[TierTransition] = []
    indices = list(session.scalars(select(IndexMeta).where(IndexMeta.enabled == True)))  # noqa: E712
    for idx in indices:
        # 拉过去 days+30 天的 valuation（先多取一点，作 baseline）
        rows = list(session.scalars(
            select(Valuation)
            .where(Valuation.index_id == idx.id)
            .where(Valuation.window == "10y")
            .where(Valuation.source == "lg")
            .order_by(Valuation.date.asc())
        ))
        # 只保留 start_date 前一日及之后
        prev: Valuation | None = None
        for v in rows:
            if v.tier is None or v.temperature is None:
                prev = v
                continue
            if v.date >= start_date and prev is not None and prev.tier is not None:
                # 找跨档跳变（或同档但温度变 ≥ 10）
                delta = v.temperature - prev.temperature
                if prev.tier != v.tier or abs(delta) >= Decimal(10):
                    sev, direction = _classify(prev.tier, v.tier, delta)
                    out.append(TierTransition(
                        entity_type="INDEX",
                        entity_code=idx.code,
                        entity_name=idx.name,
                        date=v.date,
                        from_tier=prev.tier,
                        to_tier=v.tier,
                        from_temperature=decimal_to_str(prev.temperature),
                        to_temperature=decimal_to_str(v.temperature),
                        temperature_delta=decimal_to_str(delta),
                        severity=sev,
                        direction=direction,
                    ))
            prev = v
    return out


def _scan_stock_transitions(session: Session, start_date: str) -> list[TierTransition]:
    out: list[TierTransition] = []
    stocks = list(session.scalars(select(Stock).where(Stock.enabled == True)))  # noqa: E712
    for s in stocks:
        rows = list(session.scalars(
            select(StockValuation)
            .where(StockValuation.stock_id == s.id)
            .where(StockValuation.window == "10y")
            .order_by(StockValuation.date.asc())
        ))
        prev: StockValuation | None = None
        for v in rows:
            if v.tier is None or v.temperature is None:
                prev = v
                continue
            if v.date >= start_date and prev is not None and prev.tier is not None:
                delta = v.temperature - prev.temperature
                if prev.tier != v.tier or abs(delta) >= Decimal(10):
                    sev, direction = _classify(prev.tier, v.tier, delta)
                    out.append(TierTransition(
                        entity_type="STOCK",
                        entity_code=s.code,
                        entity_name=s.name,
                        date=v.date,
                        from_tier=prev.tier,
                        to_tier=v.tier,
                        from_temperature=decimal_to_str(prev.temperature),
                        to_temperature=decimal_to_str(v.temperature),
                        temperature_delta=decimal_to_str(delta),
                        severity=sev,
                        direction=direction,
                    ))
            prev = v
    return out


def _scan_fund_transitions(session: Session, start_date: str) -> list[TierTransition]:
    """主动基金温度跳变（ETF / 指数联接温度 = 跟踪指数温度，已在 _scan_index 里）。"""
    out: list[TierTransition] = []
    funds = list(session.scalars(
        select(Fund).where(Fund.fund_type == "ACTIVE_FUND").where(Fund.enabled == True)  # noqa: E712
    ))
    for f in funds:
        rows = list(session.scalars(
            select(FundValuation)
            .where(FundValuation.fund_id == f.id)
            .where(FundValuation.window == "5y")
            .order_by(FundValuation.date.asc())
        ))
        prev: FundValuation | None = None
        for v in rows:
            if v.tier is None or v.temperature is None:
                prev = v
                continue
            if v.date >= start_date and prev is not None and prev.tier is not None:
                delta = v.temperature - prev.temperature
                if prev.tier != v.tier or abs(delta) >= Decimal(10):
                    sev, direction = _classify(prev.tier, v.tier, delta)
                    out.append(TierTransition(
                        entity_type="FUND",
                        entity_code=f.code,
                        entity_name=f.name,
                        date=v.date,
                        from_tier=prev.tier,
                        to_tier=v.tier,
                        from_temperature=decimal_to_str(prev.temperature),
                        to_temperature=decimal_to_str(v.temperature),
                        temperature_delta=decimal_to_str(delta),
                        severity=sev,
                        direction=direction,
                    ))
            prev = v
    return out


@router.get("/tier-transitions", response_model=TierTransitionsResponse)
def list_tier_transitions(
    days: int = Query(default=7, ge=1, le=90),
    severity: str | None = Query(default=None, pattern=r"^(HIGH|MEDIUM|INFO)$"),
    session: Session = Depends(db_session),
) -> TierTransitionsResponse:
    start = (date.today() - timedelta(days=days)).isoformat()
    market_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    items: list[TierTransition] = []
    items += _scan_index_transitions(session, start, market_by_id)
    items += _scan_stock_transitions(session, start)
    items += _scan_fund_transitions(session, start)

    if severity:
        items = [it for it in items if it.severity == severity]

    # 排序：日期降序，HIGH 优先
    sev_rank = {"HIGH": 0, "MEDIUM": 1, "INFO": 2}
    items.sort(key=lambda it: (it.date, -sev_rank.get(it.severity, 3)), reverse=True)

    return TierTransitionsResponse(days=days, items=items)
