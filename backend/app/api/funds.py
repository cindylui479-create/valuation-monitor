"""SRS R12 §11.3 M7-A + M7-B：基金 API。

GET    /api/v1/funds              所有基金 + 温度（按 fund_type 分流）
GET    /api/v1/funds/{code}       单只基金摘要
GET    /api/v1/funds/{code}/detail 主动基金详情：NAV 序列 + 分位历史
POST   /api/v1/funds/add          手动加入主动基金（拉 NAV 历史）
DELETE /api/v1/funds/{code}       删除主动基金（ETF / 指数联接不删）

温度规则（SRS §11.3.1）：
- ETF / INDEX_FUND：温度直接挂跟踪指数（latest_valuation 10y lg）
- ACTIVE_FUND：NAV 5y 历史百分位 × 100
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.fund_akshare_adapter import FundAkshareAdapter
from app.deps import db_session
from app.models import Fund, IndexMeta, Market
from app.repositories import fund_repo, quote_repo, valuation_repo
from app.services import fund_pipeline, fund_valuation_service
from app.utils.exceptions import FetchFailure

router = APIRouter()


class FundSummary(BaseModel):
    code: str
    name: str
    type: str
    fund_type: str                        # ETF / INDEX_FUND / ACTIVE_FUND
    market: str
    fee_rate: str | None
    tracking_error_note: str | None
    setup_date: str | None
    fund_manager: str | None
    # 估值口径
    tracks_index_code: str | None
    tracks_index_name: str | None
    temperature: str | None
    tier: str | None
    pe_ttm: str | None                   # ETF / INDEX_FUND 才有
    pb: str | None
    valuation_source: str | None         # 'index_lg' / 'index_csi' / 'nav_5y' / null
    nav_latest: str | None               # ACTIVE_FUND 最新单位净值
    actual_history_years: float | None   # ACTIVE_FUND 才有
    data_window_note: str | None


class FundListResponse(BaseModel):
    items: list[FundSummary]


class NAVPoint(BaseModel):
    date: str
    nav: str


class FundValuationPoint(BaseModel):
    date: str
    window: str
    nav_percentile: str | None
    temperature: str | None
    tier: str | None


class FundDetail(BaseModel):
    code: str
    name: str
    fund_type: str
    fund_manager: str | None
    setup_date: str | None
    market: str
    tracks_index_code: str | None
    tracks_index_name: str | None
    actual_history_years: float
    data_window_note: str | None
    latest_valuation: FundValuationPoint | None
    nav_history: list[NAVPoint]
    valuation_series: list[FundValuationPoint]


class AddFundRequest(BaseModel):
    code: str


def _fmt(v) -> str | None:
    return None if v is None else format(v, "f")


def _summary(
    session: Session, f: Fund,
    idx_by_id: dict[int, IndexMeta], mkt_by_id: dict[int, str],
) -> FundSummary:
    market_code = mkt_by_id.get(f.market_id, "?")
    if f.fund_type == "ACTIVE_FUND":
        # NAV 路径
        v = fund_repo.latest_fund_valuation(session, f.id, "5y")
        nav_latest = fund_repo.list_recent_nav(session, f.id, limit=1)
        nav_str = _fmt(nav_latest[0].nav) if nav_latest else None
        years = fund_repo.actual_history_years(session, f.id)
        return FundSummary(
            code=f.code, name=f.name, type=f.type, fund_type=f.fund_type, market=market_code,
            fee_rate=_fmt(f.fee_rate),
            tracking_error_note=f.tracking_error_note,
            setup_date=f.setup_date, fund_manager=f.fund_manager,
            tracks_index_code=None, tracks_index_name=None,
            temperature=_fmt(v.temperature) if v else None,
            tier=v.tier if v else None,
            pe_ttm=None, pb=None,
            valuation_source="nav_5y" if v else None,
            nav_latest=nav_str,
            actual_history_years=round(years, 1),
            data_window_note=fund_valuation_service.data_window_note(session, f),
        )

    # ETF / INDEX_FUND 路径：挂跟踪指数
    idx = idx_by_id.get(f.tracks_index_id) if f.tracks_index_id else None
    temp = tier = pe = pb = val_src = None
    if idx is not None:
        v, eff_src = valuation_repo.latest_with_fallback(session, idx.id, "10y", preferred="lg")
        if v is not None:
            temp = _fmt(v.temperature)
            tier = v.tier
            val_src = f"index_{eff_src}"
        recent = quote_repo.list_recent(session, idx.id, limit=1)
        if recent:
            q = recent[0]
            pe = _fmt(q.pe_ttm)
            pb = _fmt(q.pb)

    return FundSummary(
        code=f.code, name=f.name, type=f.type, fund_type=f.fund_type, market=market_code,
        fee_rate=_fmt(f.fee_rate),
        tracking_error_note=f.tracking_error_note,
        setup_date=f.setup_date, fund_manager=f.fund_manager,
        tracks_index_code=idx.code if idx else None,
        tracks_index_name=idx.name if idx else None,
        temperature=temp, tier=tier, pe_ttm=pe, pb=pb,
        valuation_source=val_src,
        nav_latest=None,
        actual_history_years=None,
        data_window_note=None,
    )


@router.get("/funds", response_model=FundListResponse)
def list_funds(session: Session = Depends(db_session)) -> FundListResponse:
    funds = list(session.scalars(select(Fund).order_by(Fund.market_id, Fund.code)))
    idx_by_id = {i.id: i for i in session.scalars(select(IndexMeta))}
    mkt_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    return FundListResponse(
        items=[_summary(session, f, idx_by_id, mkt_by_id) for f in funds]
    )


@router.get("/funds/{code}", response_model=FundSummary)
def fund_summary(code: str, session: Session = Depends(db_session)) -> FundSummary:
    f = fund_repo.get_by_code(session, code)
    if f is None:
        raise HTTPException(404, f"未找到基金 {code}")
    idx_by_id = {i.id: i for i in session.scalars(select(IndexMeta))}
    mkt_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    return _summary(session, f, idx_by_id, mkt_by_id)


@router.get("/funds/{code}/detail", response_model=FundDetail)
def fund_detail(code: str, session: Session = Depends(db_session)) -> FundDetail:
    f = fund_repo.get_by_code(session, code)
    if f is None:
        raise HTTPException(404, f"未找到基金 {code}")
    mkt_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    market_code = mkt_by_id.get(f.market_id, "?")

    idx_code = idx_name = None
    if f.tracks_index_id:
        idx = session.get(IndexMeta, f.tracks_index_id)
        if idx:
            idx_code, idx_name = idx.code, idx.name

    nav_rows = fund_repo.list_all_nav(session, f.id)
    nav_history = [NAVPoint(date=n.date, nav=_fmt(n.nav)) for n in nav_rows]
    val_series = [
        FundValuationPoint(
            date=v.date, window=v.window,
            nav_percentile=_fmt(v.nav_percentile),
            temperature=_fmt(v.temperature),
            tier=v.tier,
        )
        for v in fund_repo.fund_valuation_series(session, f.id, window="5y")
    ]
    latest = fund_repo.latest_fund_valuation(session, f.id, "5y")
    latest_v = FundValuationPoint(
        date=latest.date, window=latest.window,
        nav_percentile=_fmt(latest.nav_percentile),
        temperature=_fmt(latest.temperature),
        tier=latest.tier,
    ) if latest else None

    return FundDetail(
        code=f.code, name=f.name, fund_type=f.fund_type,
        fund_manager=f.fund_manager, setup_date=f.setup_date, market=market_code,
        tracks_index_code=idx_code, tracks_index_name=idx_name,
        actual_history_years=round(fund_repo.actual_history_years(session, f.id), 1),
        data_window_note=fund_valuation_service.data_window_note(session, f),
        latest_valuation=latest_v,
        nav_history=nav_history,
        valuation_series=val_series,
    )


@router.post("/funds/add", response_model=FundSummary)
def add_active_fund(req: AddFundRequest, session: Session = Depends(db_session)) -> FundSummary:
    """手动加入场外主动基金。

    流程：调 akshare 取基金信息 → 判定是否主动型 → 新建 Fund → 拉 NAV 全历史 → 重算分位。
    """
    code = req.code.strip()
    if not code:
        raise HTTPException(400, "基金代码不能为空")

    existing = fund_repo.get_by_code(session, code)
    if existing is not None:
        raise HTTPException(409, f"基金 {code} 已存在（{existing.name} · {existing.fund_type}）")

    adapter = FundAkshareAdapter()
    try:
        info = adapter.fetch_info(code)
    except FetchFailure as e:
        raise HTTPException(400, f"获取基金信息失败：{e}")

    if not info.is_active:
        raise HTTPException(
            400,
            f"基金类型 '{info.fund_type_raw}' 看起来不是主动基金。"
            f"ETF / 指数基金请通过内置池管理，本接口仅支持场外主动基金。"
        )

    market = session.query(Market).filter_by(code="A").first()
    if market is None:
        raise HTTPException(500, "A 市场未初始化")

    fund = fund_repo.add_active_fund(
        session,
        code=info.code, name=info.name, market_id=market.id,
        setup_date=info.setup_date, fund_manager=info.fund_manager,
        fund_type_raw=info.fund_type_raw,
    )
    session.commit()

    result = fund_pipeline.init_fund_history(session, fund)
    if result.error:
        raise HTTPException(503, f"已加入但拉 NAV 失败：{result.error}")

    idx_by_id = {i.id: i for i in session.scalars(select(IndexMeta))}
    mkt_by_id = {m.id: m.code for m in session.scalars(select(Market))}
    return _summary(session, fund, idx_by_id, mkt_by_id)


@router.delete("/funds/{code}", status_code=204)
def delete_fund(code: str, session: Session = Depends(db_session)):
    f = fund_repo.get_by_code(session, code)
    if f is None:
        raise HTTPException(404, f"未找到 {code}")
    if f.fund_type != "ACTIVE_FUND":
        raise HTTPException(400, f"仅支持删除主动基金；{code} 为 {f.fund_type}（内置池基金）")

    from app.models import FundNAV, FundValuation
    session.query(FundValuation).filter_by(fund_id=f.id).delete()
    session.query(FundNAV).filter_by(fund_id=f.id).delete()
    session.delete(f)
    session.commit()
