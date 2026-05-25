from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import db_session
from app.errors import BusinessRuleViolation, NotFound
from app.models import Market
from app.repositories import index_repo, quote_repo, valuation_repo, watchlist_repo
from app.schemas.watchlist import WatchlistCreate, WatchlistItem
from app.services.valuation_service import (
    actual_history_years,
    data_window_note,
)
from app.utils.decimal_utils import decimal_to_str
from app.utils.time_utils import now_iso

router = APIRouter()


def _build_item(
    session: Session,
    w,
    idx,
    pe_source: str,
    market_codes: dict[int, str],
) -> WatchlistItem:
    """加权返回单条 watchlist 项：含 latest_valuation 温度 + 当日 PE/PB + 实际历史。

    沿用与 overview API 一致的 latest_with_fallback 规则（参见 §R10）。
    """
    v_with_src = valuation_repo.latest_with_fallback(
        session, idx.id, window="10y", preferred=pe_source
    )
    v = v_with_src[0] if v_with_src else None
    effective_source = v_with_src[1] if v_with_src else None

    quotes = quote_repo.list_recent(session, idx.id, limit=1)
    q = quotes[0] if quotes else None

    pe_field = "pe_ttm_csi" if effective_source == "csi" and pe_source == "csi" else "pe_ttm"
    pb_field = "pb_csi" if effective_source == "csi" and pe_source == "csi" else "pb"

    return WatchlistItem(
        id=w.id,
        index_code=idx.code,
        index_name=idx.name,
        market=market_codes.get(idx.market_id),
        category=idx.category,
        industry_raw=idx.industry_raw,
        tag=w.tag,
        added_at=w.added_at,
        temperature=decimal_to_str(v.temperature) if v else None,
        tier=v.tier if v else None,
        pe_ttm=decimal_to_str(getattr(q, pe_field, None)) if q else None,
        pb=decimal_to_str(getattr(q, pb_field, None)) if q else None,
        dividend_yield=decimal_to_str(q.dividend_yield) if q else None,
        valuation_source=effective_source,
        temperature_source=(v.temperature_source if v else None),
        actual_history_years=round(actual_history_years(session, idx), 1) if idx else None,
        data_window_note=data_window_note(session, idx) if idx else None,
    )


@router.get("/watchlist", response_model=list[WatchlistItem])
def list_watchlist(
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    session: Session = Depends(db_session),
) -> list[WatchlistItem]:
    market_codes = {m.id: m.code for m in session.query(Market).all()}
    out: list[WatchlistItem] = []
    for w, idx in watchlist_repo.list_all(session):
        out.append(_build_item(session, w, idx, pe_source, market_codes))
    return out


@router.post("/watchlist", response_model=WatchlistItem, status_code=201)
def add_watchlist(
    body: WatchlistCreate,
    pe_source: str = Query(default="lg", pattern=r"^(lg|csi)$"),
    session: Session = Depends(db_session),
) -> WatchlistItem:
    idx = index_repo.get_by_code(session, body.index_code)
    if idx is None:
        raise NotFound("index not found", code=body.index_code)
    existing = watchlist_repo.get_for_index(session, idx.id, body.tag)
    if existing is not None:
        raise BusinessRuleViolation(
            "index already in watchlist with this tag",
            code=body.index_code,
            tag=body.tag,
        )
    w = watchlist_repo.add(session, idx.id, body.tag, added_at=now_iso())
    session.commit()
    market_codes = {m.id: m.code for m in session.query(Market).all()}
    return _build_item(session, w, idx, pe_source, market_codes)


@router.delete("/watchlist/{watchlist_id}", status_code=204)
def remove_watchlist(watchlist_id: int, session: Session = Depends(db_session)) -> None:
    ok = watchlist_repo.delete_by_id(session, watchlist_id)
    if not ok:
        raise NotFound("watchlist entry not found", id=watchlist_id)
    session.commit()
