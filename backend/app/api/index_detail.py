"""GET /api/v1/indices/{code}/detail — 详情页一次性返回元信息 + 近 N 天的 quote + valuation 序列。

只读端点，未来 M4 可扩展含信号 / 定投。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import NotFound
from app.models import Market
from app.models import Signal
from app.repositories import index_repo, quote_repo, valuation_repo
from app.schemas.index import FundDTO
from app.schemas.index_detail import (
    IndexDetailResponse,
    QuotePoint,
    SignalPoint,
    ValuationPoint,
)
from sqlalchemy import select
from app.services.valuation_service import actual_history_years, data_window_note
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


@router.get("/indices/{code}/detail", response_model=IndexDetailResponse)
def get_index_detail(
    code: str,
    days: int = Query(default=2500, ge=1, le=5000),
    window: str = Query(default="10y", pattern=r"^(5y|10y|all)$"),
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    session: Session = Depends(db_session),
) -> IndexDetailResponse:
    idx = index_repo.get_by_code(session, code)
    if idx is None:
        raise NotFound("index not found", code=code)

    market = session.get(Market, idx.market_id)
    funds = index_repo.funds_for(session, idx.id)

    quotes = quote_repo.list_recent(session, idx.id, limit=days)
    quotes.sort(key=lambda q: q.date)

    # SRS R10：按口径取 valuation 序列；若该指数偏好源无数据 → fallback 到另一个
    val_rows = valuation_repo.series(session, idx.id, window=window, source=pe_source)
    if not val_rows:
        alt = "csi" if pe_source == "lg" else "lg"
        val_rows = valuation_repo.series(session, idx.id, window=window, source=alt)
    val_by_date = {v.date: v for v in val_rows}

    # 按口径选 pe/pb 字段
    def _pe(q):
        if pe_source == "csi":
            return q.pe_ttm_csi if q.pe_ttm_csi is not None else q.pe_ttm
        return q.pe_ttm if q.pe_ttm is not None else q.pe_ttm_csi

    def _pb(q):
        if pe_source == "csi":
            return q.pb_csi if q.pb_csi is not None else q.pb
        return q.pb if q.pb is not None else q.pb_csi

    quote_points = [
        QuotePoint(
            date=q.date,
            close=decimal_to_str(q.close) or "0",
            pe_ttm=decimal_to_str(_pe(q)),
            pb=decimal_to_str(_pb(q)),
            dividend_yield=decimal_to_str(q.dividend_yield),
        )
        for q in quotes
    ]
    val_points = [
        ValuationPoint(
            date=v.date,
            pe_percentile=decimal_to_str(v.pe_percentile),
            pb_percentile=decimal_to_str(v.pb_percentile),
            temperature=decimal_to_str(v.temperature),
            tier=v.tier,
            temperature_source=v.temperature_source,
        )
        for v in val_rows
    ]
    latest_with_src = valuation_repo.latest_with_fallback(
        session, idx.id, window="10y", preferred=pe_source
    )
    latest_v = latest_with_src[0] if latest_with_src else None
    latest_point = (
        ValuationPoint(
            date=latest_v.date,
            pe_percentile=decimal_to_str(latest_v.pe_percentile),
            pb_percentile=decimal_to_str(latest_v.pb_percentile),
            temperature=decimal_to_str(latest_v.temperature),
            tier=latest_v.tier,
            temperature_source=latest_v.temperature_source,
        )
        if latest_v
        else None
    )

    _ = val_by_date  # reserved for future merge logic if needed

    # 信号历史（按日期倒序，最多 200 条）
    signal_rows = list(
        session.scalars(
            select(Signal).where(Signal.index_id == idx.id).order_by(Signal.date.desc()).limit(200)
        )
    )
    signal_points = [
        SignalPoint(
            date=s.date,
            direction=s.direction,
            tier=s.tier,
            temperature=decimal_to_str(s.temperature) or "0",
        )
        for s in signal_rows
    ]
    latest_signal = signal_points[0] if signal_points else None

    return IndexDetailResponse(
        code=idx.code,
        name=idx.name,
        market=market.code if market else "",
        currency=market.currency if market else "",
        category=idx.category,
        industry_raw=idx.industry_raw,
        history_start_date=idx.history_start_date,
        actual_history_years=round(actual_history_years(session, idx), 2),
        data_window_note=data_window_note(session, idx),
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
        latest_valuation=latest_point,
        latest_signal=latest_signal,
        signal_history=signal_points,
        quotes=quote_points,
        valuation_series=val_points,
    )
