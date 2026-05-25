from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Market
from app.repositories import index_repo, quote_repo, valuation_repo
from app.schemas.overview import OverviewIndex, OverviewMarket, OverviewResponse
from app.services.valuation_service import data_window_note
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    session: Session = Depends(db_session),
) -> OverviewResponse:
    """SRS R10：pe_source 决定温度/分位口径。若该指数在偏好源无数据则 fallback。"""
    markets = session.query(Market).order_by(Market.id).all()
    out_markets: list[OverviewMarket] = []
    as_of: str | None = None

    for m in markets:
        indices = index_repo.list_indices(session, market_code=m.code)
        out_indices: list[OverviewIndex] = []
        for idx in indices:
            v_with_src = valuation_repo.latest_with_fallback(
                session, idx.id, window="10y", preferred=pe_source
            )
            v = v_with_src[0] if v_with_src else None
            effective_source = v_with_src[1] if v_with_src else None

            q = quote_repo.list_recent(session, idx.id, limit=1)
            quote = q[0] if q else None

            # 当日 PE：按 source 选 pe_ttm 或 pe_ttm_csi（fallback 互补）
            display_pe = _pick_pe_field(quote, pe_source) if quote else None
            display_pb = _pick_pb_field(quote, pe_source) if quote else None

            if v is not None and (as_of is None or v.date > as_of):
                as_of = v.date

            ma50_dev = _safe_div_sub(quote.close, quote.ma50) if quote else None
            ma200_dev = _safe_div_sub(quote.close, quote.ma200) if quote else None

            funds = index_repo.funds_for(session, idx.id)

            # data_window_note 标注"用了哪个源"
            note = data_window_note(session, idx)
            if effective_source is not None and effective_source != pe_source:
                fallback_tag = f"({effective_source.upper()} fallback)"
                note = f"{note} {fallback_tag}" if note else fallback_tag

            out_indices.append(
                OverviewIndex(
                    code=idx.code,
                    name=idx.name,
                    category=idx.category,
                    tier=(v.tier if v else None),
                    temperature=decimal_to_str(v.temperature) if v else None,
                    pe_ttm=decimal_to_str(display_pe),
                    pe_percentile_10y=decimal_to_str(v.pe_percentile) if v else None,
                    pb_percentile_10y=decimal_to_str(v.pb_percentile) if v else None,
                    dividend_yield=decimal_to_str(quote.dividend_yield) if quote else None,
                    ma50_deviation=decimal_to_str(ma50_dev),
                    ma200_deviation=decimal_to_str(ma200_dev),
                    data_window_note=note,
                    temperature_source=(v.temperature_source if v else None),
                    funds_count=len(funds),
                )
            )
            _ = display_pb  # PB 暂未在 OverviewIndex 字段中

        out_markets.append(
            OverviewMarket(market=m.code, currency=m.currency, indices=out_indices)
        )

    return OverviewResponse(as_of=as_of, markets=out_markets)


def _pick_pe_field(quote, source: str) -> Decimal | None:
    """按口径偏好选 pe_ttm 或 pe_ttm_csi；该源为空时 fallback 到另一个。"""
    if source == "csi":
        return quote.pe_ttm_csi if quote.pe_ttm_csi is not None else quote.pe_ttm
    return quote.pe_ttm if quote.pe_ttm is not None else quote.pe_ttm_csi


def _pick_pb_field(quote, source: str) -> Decimal | None:
    if source == "csi":
        return quote.pb_csi if quote.pb_csi is not None else quote.pb
    return quote.pb if quote.pb is not None else quote.pb_csi


def _safe_div_sub(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None or b == 0:
        return None
    return (a - b) / b
