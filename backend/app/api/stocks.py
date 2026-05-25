"""SRS R12 §11.2.6：A 股个股 API。

POST  /stocks/add            手动加入自选 + 触发拉历史（同步等待，<10s）
GET   /stocks                自选个股列表 + 最新温度
GET   /stocks/{code}/detail  个股详情：行情序列 + valuation 序列 + 最新档位
PATCH /stocks/{code}/anchor  覆盖估值锚
DELETE /stocks/{code}        删除自选（连带 quote / valuation cascade，业务上保留历史）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.adapters.stock_tushare_adapter import StockTushareAdapter
from app.deps import db_session
from app.models import Market
from app.repositories import stock_repo
from app.services import stock_pipeline, stock_valuation_service
from app.utils.exceptions import FetchFailure
from app.valuation.anchor import ALL_ANCHORS, default_anchor_for_industry

router = APIRouter()


class AddStockRequest(BaseModel):
    code: str


class StockSummary(BaseModel):
    code: str
    name: str
    industry: str | None
    anchor: str
    listing_date: str | None
    temperature: str | None
    tier: str | None
    pe_ttm: str | None
    pb: str | None
    ps_ttm: str | None
    actual_history_years: float
    data_window_note: str | None


class StockListResponse(BaseModel):
    items: list[StockSummary]


class QuotePoint(BaseModel):
    date: str
    close: str
    pe_ttm: str | None
    pb: str | None
    ps_ttm: str | None
    dividend_yield: str | None


class ValuationPoint(BaseModel):
    date: str
    window: str
    anchor: str
    pe_percentile: str | None
    pb_percentile: str | None
    ps_percentile: str | None
    dy_percentile: str | None
    temperature: str | None
    tier: str | None


class AnchorComparison(BaseModel):
    """SRS v1.3.0 J：5 种锚下的温度对比（让用户在切换前看见）。"""
    anchor: str
    temperature: str | None
    tier: str | None
    available: bool          # 该字段是否有足够分位数据


class StockDetail(BaseModel):
    code: str
    name: str
    industry: str | None
    anchor: str
    available_anchors: list[str]
    listing_date: str | None
    status: str
    actual_history_years: float
    data_window_note: str | None
    latest_valuation: ValuationPoint | None
    quotes: list[QuotePoint]
    valuation_series: list[ValuationPoint]
    # SRS v1.3.0 J：所有锚的温度对比 + 当前行业建议
    anchor_comparisons: list[AnchorComparison] = []
    industry_default_anchor: str | None = None  # 该行业的"行业默认推荐"


class AnchorUpdate(BaseModel):
    anchor: str


def _fmt(d) -> str | None:
    return None if d is None else format(d, "f")


def _summary(session: Session, s) -> StockSummary:
    v = stock_repo.latest_valuation(session, s.id)
    latest_quote = stock_repo.list_recent_quotes(session, s.id, limit=1)
    q = latest_quote[0] if latest_quote else None
    return StockSummary(
        code=s.code, name=s.name, industry=s.industry_raw,
        anchor=stock_valuation_service.effective_anchor(session, s),
        listing_date=s.listing_date,
        temperature=_fmt(v.temperature) if v else None,
        tier=v.tier if v else None,
        pe_ttm=_fmt(q.pe_ttm) if q else None,
        pb=_fmt(q.pb) if q else None,
        ps_ttm=_fmt(q.ps_ttm) if q else None,
        actual_history_years=round(stock_repo.actual_history_years(session, s.id), 1),
        data_window_note=stock_valuation_service.data_window_note(session, s),
    )


@router.post("/stocks/add", response_model=StockSummary)
def add_stock(req: AddStockRequest, session: Session = Depends(db_session)) -> StockSummary:
    """加入自选 → Tushare stock_basic 取行业 / 上市日 → 拉上市以来全历史。"""
    code = req.code.strip().upper()
    if not code:
        raise HTTPException(400, "股票代码不能为空")

    adapter = StockTushareAdapter()
    try:
        info = adapter.fetch_info(code)
    except FetchFailure as e:
        raise HTTPException(400, f"获取股票信息失败：{e}")

    existing = stock_repo.get_by_code(session, info.code)
    if existing is not None:
        raise HTTPException(409, f"股票 {info.code} 已在自选")

    market = session.query(Market).filter_by(code="A").first()
    if market is None:
        raise HTTPException(500, "A 市场未初始化（请先跑 seed_universe）")

    anchor = default_anchor_for_industry(info.industry_raw)
    stock = stock_repo.add_stock(
        session,
        code=info.code, name=info.name, market_id=market.id,
        industry_raw=info.industry_raw, listing_date=info.listing_date,
        valuation_anchor=anchor,
    )
    session.commit()

    # 拉历史（同步）。茅台 3967 行 ≈ 8–10 秒
    result = stock_pipeline.init_stock_history(session, stock)
    if result.error:
        # 个股已入库但拉数失败 — 保留实体，让用户后续重试
        raise HTTPException(503, f"已加入自选但拉历史失败：{result.error}")

    return _summary(session, stock)


@router.get("/stocks", response_model=StockListResponse)
def list_stocks(session: Session = Depends(db_session)) -> StockListResponse:
    stocks = stock_repo.list_stocks(session)
    return StockListResponse(items=[_summary(session, s) for s in stocks])


@router.get("/stocks/{code}/detail", response_model=StockDetail)
def stock_detail(code: str, session: Session = Depends(db_session)) -> StockDetail:
    s = stock_repo.get_by_code(session, code)
    if s is None:
        raise HTTPException(404, f"未找到 {code}")

    anchor = stock_valuation_service.effective_anchor(session, s)
    latest_v = stock_repo.latest_valuation(session, s.id)
    quotes = list(reversed(stock_repo.list_recent_quotes(session, s.id, limit=3000)))
    series = stock_repo.valuation_series(session, s.id, window="10y")

    # SRS v1.3.0 J：算 5 种锚下的温度（从 latest_valuation 的百分位反推）
    from app.valuation.anchor import temperature_from_anchor
    from app.valuation import tier_of, DEFAULT_BOUNDARIES
    from decimal import Decimal
    comparisons: list[AnchorComparison] = []
    if latest_v is not None:
        for anc in ALL_ANCHORS:
            t = temperature_from_anchor(
                anc,
                pe_pctl=latest_v.pe_percentile,
                pb_pctl=latest_v.pb_percentile,
                ps_pctl=latest_v.ps_percentile,
                dy_pctl=latest_v.dy_percentile,
            )
            if t is not None:
                tier_pctl = t / Decimal(100)
                tier = tier_of(tier_pctl, DEFAULT_BOUNDARIES)
                comparisons.append(AnchorComparison(
                    anchor=anc, temperature=_fmt(t), tier=tier, available=True,
                ))
            else:
                comparisons.append(AnchorComparison(
                    anchor=anc, temperature=None, tier=None, available=False,
                ))

    return StockDetail(
        code=s.code, name=s.name, industry=s.industry_raw,
        anchor=anchor, available_anchors=list(ALL_ANCHORS),
        listing_date=s.listing_date, status=s.status,
        actual_history_years=round(stock_repo.actual_history_years(session, s.id), 1),
        data_window_note=stock_valuation_service.data_window_note(session, s),
        latest_valuation=_v_point(latest_v) if latest_v else None,
        quotes=[_q_point(q) for q in quotes],
        valuation_series=[_v_point(v) for v in series],
        anchor_comparisons=comparisons,
        industry_default_anchor=default_anchor_for_industry(s.industry_raw),
    )


@router.patch("/stocks/{code}/anchor", response_model=StockSummary)
def update_anchor(
    code: str, body: AnchorUpdate, session: Session = Depends(db_session),
) -> StockSummary:
    if body.anchor not in ALL_ANCHORS:
        raise HTTPException(400, f"未知锚: {body.anchor}")
    s = stock_repo.get_by_code(session, code)
    if s is None:
        raise HTTPException(404, f"未找到 {code}")
    stock_repo.upsert_override(session, s.id, valuation_anchor=body.anchor)
    session.flush()  # 确保 recompute 时 effective_anchor 能立即读到新 override
    # 立即重算近 30 天温度
    from datetime import date, timedelta
    today = date.today()
    recent = [(today - timedelta(days=i)).isoformat() for i in range(30)]
    stock_valuation_service.recompute_for_stock(session, s, recent)
    session.commit()
    return _summary(session, s)


@router.delete("/stocks/{code}", status_code=204)
def delete_stock(code: str, session: Session = Depends(db_session)):
    s = stock_repo.get_by_code(session, code)
    if s is None:
        raise HTTPException(404, f"未找到 {code}")
    # MVP：硬删除（连带 quote / valuation cascade）
    from app.models import StockOverride, StockQuote, StockValuation
    session.query(StockOverride).filter_by(stock_id=s.id).delete()
    session.query(StockValuation).filter_by(stock_id=s.id).delete()
    session.query(StockQuote).filter_by(stock_id=s.id).delete()
    session.delete(s)
    session.commit()


def _q_point(q) -> QuotePoint:
    return QuotePoint(
        date=q.date, close=_fmt(q.close),
        pe_ttm=_fmt(q.pe_ttm), pb=_fmt(q.pb), ps_ttm=_fmt(q.ps_ttm),
        dividend_yield=_fmt(q.dv_ttm),
    )


def _v_point(v) -> ValuationPoint:
    return ValuationPoint(
        date=v.date, window=v.window, anchor=v.anchor,
        pe_percentile=_fmt(v.pe_percentile),
        pb_percentile=_fmt(v.pb_percentile),
        ps_percentile=_fmt(v.ps_percentile),
        dy_percentile=_fmt(v.dy_percentile),
        temperature=_fmt(v.temperature),
        tier=v.tier,
    )
