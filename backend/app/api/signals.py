from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Market
from app.repositories import signal_repo
from app.schemas.signal import SignalDTO, SignalListResponse
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


def _to_dto(s, idx, market_code: str) -> SignalDTO:
    return SignalDTO(
        id=s.id,
        index_code=idx.code,
        index_name=idx.name,
        market=market_code,
        date=s.date,
        direction=s.direction,
        tier=s.tier,
        temperature=decimal_to_str(s.temperature) or "0",
        generated_at=s.generated_at,
    )


@router.get("/signals", response_model=SignalListResponse)
def list_signals(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    market: str | None = Query(default=None),
    direction: str | None = Query(default=None, pattern=r"^(STRONG_BUY|BUY|SELL|STRONG_SELL)$"),
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    only_subscribed: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(db_session),
) -> SignalListResponse:
    rows = signal_repo.list_signals(
        session,
        date_from=date_from, date_to=date_to,
        market_code=market, direction=direction,
        source=pe_source,
        only_subscribed=only_subscribed, limit=limit, offset=offset,
    )
    market_map = {m.id: m.code for m in session.scalars(select(Market)).all()}
    return SignalListResponse(
        items=[_to_dto(s, idx, market_map.get(idx.market_id, "")) for s, idx in rows],
        total=len(rows),
    )


@router.get("/signals/today", response_model=SignalListResponse)
def signals_today(
    market: str | None = Query(default=None),
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    only_subscribed: bool = Query(default=False),
    session: Session = Depends(db_session),
) -> SignalListResponse:
    """今日信号；如今日无数据回退到最近一日。"""
    today = date.today().isoformat()
    rows = signal_repo.list_signals(
        session, date_from=today, date_to=today, market_code=market,
        source=pe_source, only_subscribed=only_subscribed, limit=500,
    )
    if not rows:
        recent_from = (date.today() - timedelta(days=30)).isoformat()
        rows_all = signal_repo.list_signals(
            session, date_from=recent_from, market_code=market,
            source=pe_source, only_subscribed=only_subscribed, limit=500,
        )
        if rows_all:
            latest_date = rows_all[0][0].date
            rows = [r for r in rows_all if r[0].date == latest_date]

    market_map = {m.id: m.code for m in session.scalars(select(Market)).all()}
    return SignalListResponse(
        items=[_to_dto(s, idx, market_map.get(idx.market_id, "")) for s, idx in rows],
        total=len(rows),
    )
