"""SRS v1.2.0 S#3：用户持仓 + 加权温度 API。

GET    /holdings                 持仓列表 + 加权温度 + 档位分布
POST   /holdings                 加一条
PATCH  /holdings/{id}            修改市值/备注
DELETE /holdings/{id}            删除
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import (
    Fund,
    Holding,
    IndexMeta,
    Stock,
)
from app.repositories import (
    fund_repo,
    quote_repo,
    stock_repo,
    valuation_repo,
)
from app.utils.decimal_utils import decimal_to_str
from app.utils.time_utils import now_iso

router = APIRouter()

VALID_ENTITY_TYPES = ("INDEX", "STOCK", "FUND")


# ============ Schemas ============
class HoldingItem(BaseModel):
    id: int
    entity_type: str
    entity_code: str
    entity_name: str | None             # 解析后的名称
    market_value: str                    # Decimal as string（按数量时实时算 = quantity × latest_price）
    quantity: str | None                 # 股数/份数（按数量录入时填）
    latest_price: str | None             # 实时单价（按数量录入时显示）
    input_mode: str                      # 'value' or 'quantity'
    weight_pct: str | None
    temperature: str | None
    tier: str | None
    temperature_source: str | None
    pe_ttm: str | None
    pb: str | None
    note: str | None
    added_at: str
    updated_at: str


class PortfolioSummary(BaseModel):
    total_value: str                     # 总市值（所有 holding 之和）
    weighted_temperature: str | None     # 基于有温度部分加权
    valued_value: str                    # 有温度的市值之和
    coverage_pct: str                    # valued_value / total_value
    tier_distribution: dict[str, str]    # tier → 市值占比
    items: list[HoldingItem]


class AddHoldingRequest(BaseModel):
    entity_type: str = Field(..., pattern=r"^(INDEX|STOCK|FUND)$")
    entity_code: str = Field(..., min_length=1, max_length=32)
    # market_value 与 quantity 二选一（quantity 优先，会按当前 close 算 mv）
    market_value: float | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=64)


class UpdateHoldingRequest(BaseModel):
    market_value: float | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=64)


# ============ 温度解析（按 entity_type 分流） ============
def _resolve_entity(session: Session, ht: str, code: str) -> dict:
    """返回 {name, temperature, tier, temperature_source, pe_ttm, pb, latest_price}。

    全部为 None 时表示找不到该实体或无估值数据。
    latest_price 用于按数量计算市值（INDEX/STOCK 是 close；FUND 是 nav 或跟踪指数 close）。
    """
    out = {
        "name": None, "temperature": None, "tier": None,
        "temperature_source": None, "pe_ttm": None, "pb": None,
        "latest_price": None,
    }

    if ht == "INDEX":
        idx = session.scalar(select(IndexMeta).where(IndexMeta.code == code))
        if idx is None:
            return out
        out["name"] = idx.name
        v_with_src = valuation_repo.latest_with_fallback(session, idx.id, "10y", preferred="lg")
        if v_with_src:
            v = v_with_src[0]
            out["temperature"] = decimal_to_str(v.temperature)
            out["tier"] = v.tier
            out["temperature_source"] = v.temperature_source
        recent = quote_repo.list_recent(session, idx.id, limit=1)
        if recent:
            out["pe_ttm"] = decimal_to_str(recent[0].pe_ttm)
            out["pb"] = decimal_to_str(recent[0].pb)
            out["latest_price"] = decimal_to_str(recent[0].close)

    elif ht == "STOCK":
        s = stock_repo.get_by_code(session, code)
        if s is None:
            return out
        out["name"] = s.name
        v = stock_repo.latest_valuation(session, s.id)
        if v is not None:
            out["temperature"] = decimal_to_str(v.temperature)
            out["tier"] = v.tier
            out["temperature_source"] = "pe_10y"
        latest_q = stock_repo.list_recent_quotes(session, s.id, limit=1)
        if latest_q:
            out["pe_ttm"] = decimal_to_str(latest_q[0].pe_ttm)
            out["pb"] = decimal_to_str(latest_q[0].pb)
            out["latest_price"] = decimal_to_str(latest_q[0].close)

    elif ht == "FUND":
        f = fund_repo.get_by_code(session, code)
        if f is None:
            return out
        out["name"] = f.name
        # ACTIVE_FUND 用 fund_valuation；其他挂跟踪指数
        if f.fund_type == "ACTIVE_FUND":
            v = fund_repo.latest_fund_valuation(session, f.id, "5y")
            if v is not None:
                out["temperature"] = decimal_to_str(v.temperature)
                out["tier"] = v.tier
                out["temperature_source"] = "nav_5y"
            # 主动基金最新 NAV 作为单价
            latest_nav = fund_repo.list_recent_nav(session, f.id, limit=1)
            if latest_nav:
                out["latest_price"] = decimal_to_str(latest_nav[0].nav)
        elif f.tracks_index_id:
            v_with_src = valuation_repo.latest_with_fallback(
                session, f.tracks_index_id, "10y", preferred="lg"
            )
            if v_with_src:
                v = v_with_src[0]
                out["temperature"] = decimal_to_str(v.temperature)
                out["tier"] = v.tier
                out["temperature_source"] = v.temperature_source
            recent = quote_repo.list_recent(session, f.tracks_index_id, limit=1)
            if recent:
                out["pe_ttm"] = decimal_to_str(recent[0].pe_ttm)
                out["pb"] = decimal_to_str(recent[0].pb)
                # ETF / 指数联接基金：单价用跟踪指数 close（用户自己换算 ETF 价格 ≈ 指数点位×ETF系数）
                out["latest_price"] = decimal_to_str(recent[0].close)
    return out


def _effective_market_value(h: Holding, info: dict) -> Decimal:
    """按数量录入时：mv = quantity × latest_price（如有）；否则取存量 market_value。"""
    if h.quantity is not None and info.get("latest_price"):
        try:
            return Decimal(str(h.quantity)) * Decimal(info["latest_price"])
        except Exception:
            pass
    return h.market_value


def _build_summary(session: Session, holdings: list[Holding]) -> PortfolioSummary:
    items: list[HoldingItem] = []
    total = Decimal(0)
    valued = Decimal(0)
    weighted_temp_num = Decimal(0)
    tier_mv: dict[str, Decimal] = {}

    resolved = []
    for h in holdings:
        info = _resolve_entity(session, h.entity_type, h.entity_code)
        eff_mv = _effective_market_value(h, info)
        resolved.append((h, info, eff_mv))
        total += eff_mv
        if info["temperature"] is not None:
            t = Decimal(info["temperature"])
            valued += eff_mv
            weighted_temp_num += eff_mv * t
            tier = info["tier"] or "未分类"
            tier_mv[tier] = tier_mv.get(tier, Decimal(0)) + eff_mv

    weighted_temp = (weighted_temp_num / valued) if valued > 0 else None
    coverage = (valued / total * Decimal(100)) if total > 0 else Decimal(0)
    tier_dist = {
        k: format(v / valued * Decimal(100), ".2f")
        for k, v in tier_mv.items()
    } if valued > 0 else {}

    for h, info, eff_mv in resolved:
        weight = (eff_mv / total * Decimal(100)) if total > 0 else None
        items.append(HoldingItem(
            id=h.id,
            entity_type=h.entity_type,
            entity_code=h.entity_code,
            entity_name=info["name"],
            market_value=decimal_to_str(eff_mv) or "0",
            quantity=decimal_to_str(h.quantity),
            latest_price=info.get("latest_price"),
            input_mode="quantity" if h.quantity is not None else "value",
            weight_pct=format(weight, ".2f") if weight is not None else None,
            temperature=info["temperature"],
            tier=info["tier"],
            temperature_source=info["temperature_source"],
            pe_ttm=info["pe_ttm"],
            pb=info["pb"],
            note=h.note,
            added_at=h.added_at,
            updated_at=h.updated_at,
        ))

    return PortfolioSummary(
        total_value=decimal_to_str(total) or "0",
        weighted_temperature=decimal_to_str(weighted_temp) if weighted_temp is not None else None,
        valued_value=decimal_to_str(valued) or "0",
        coverage_pct=decimal_to_str(coverage) or "0",
        tier_distribution=tier_dist,
        items=items,
    )


# ============ Endpoints ============
@router.get("/holdings", response_model=PortfolioSummary)
def list_holdings(session: Session = Depends(db_session)) -> PortfolioSummary:
    holdings = list(session.scalars(select(Holding).order_by(Holding.id)))
    return _build_summary(session, holdings)


@router.post("/holdings", response_model=HoldingItem, status_code=201)
def add_holding(
    body: AddHoldingRequest, session: Session = Depends(db_session),
) -> HoldingItem:
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(400, f"未知 entity_type: {body.entity_type}")
    if body.market_value is None and body.quantity is None:
        raise HTTPException(400, "需提供 market_value 或 quantity 之一")

    entity_code = body.entity_code.strip()

    # 按数量录入时，立即拉最新单价 × 数量算 snapshot mv（quantity 会保留，每次查询会重算）
    snapshot_mv: Decimal
    quantity_dec: Decimal | None = None
    if body.quantity is not None:
        info = _resolve_entity(session, body.entity_type, entity_code)
        price = info.get("latest_price")
        if not price:
            raise HTTPException(
                400,
                f"无法取得 {entity_code} 最新单价（实体可能不在跟踪库内）。"
                f"请改用「按金额」模式，或先到自选页加入。",
            )
        quantity_dec = Decimal(str(body.quantity))
        snapshot_mv = quantity_dec * Decimal(price)
    else:
        snapshot_mv = Decimal(str(body.market_value))

    h = Holding(
        entity_type=body.entity_type,
        entity_code=entity_code,
        market_value=snapshot_mv,
        quantity=quantity_dec,
        note=body.note,
        added_at=now_iso(),
        updated_at=now_iso(),
    )
    session.add(h)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(409, f"持仓已存在或冲突：{e}")

    info = _resolve_entity(session, h.entity_type, h.entity_code)
    eff_mv = _effective_market_value(h, info)
    return HoldingItem(
        id=h.id, entity_type=h.entity_type, entity_code=h.entity_code,
        entity_name=info["name"],
        market_value=decimal_to_str(eff_mv) or "0",
        quantity=decimal_to_str(h.quantity),
        latest_price=info.get("latest_price"),
        input_mode="quantity" if h.quantity is not None else "value",
        weight_pct=None,
        temperature=info["temperature"], tier=info["tier"],
        temperature_source=info["temperature_source"],
        pe_ttm=info["pe_ttm"], pb=info["pb"],
        note=h.note, added_at=h.added_at, updated_at=h.updated_at,
    )


@router.patch("/holdings/{holding_id}", response_model=HoldingItem)
def update_holding(
    holding_id: int, body: UpdateHoldingRequest,
    session: Session = Depends(db_session),
) -> HoldingItem:
    h = session.get(Holding, holding_id)
    if h is None:
        raise HTTPException(404, f"未找到持仓 {holding_id}")
    if body.quantity is not None:
        # 切换到 quantity 模式：拉最新价 × 数量 → snapshot mv
        info = _resolve_entity(session, h.entity_type, h.entity_code)
        price = info.get("latest_price")
        if not price:
            raise HTTPException(400, f"无最新单价，无法按数量更新")
        h.quantity = Decimal(str(body.quantity))
        h.market_value = h.quantity * Decimal(price)
    elif body.market_value is not None:
        h.market_value = Decimal(str(body.market_value))
        h.quantity = None  # 切回 value 模式
    if body.note is not None:
        h.note = body.note
    h.updated_at = now_iso()
    session.commit()
    info = _resolve_entity(session, h.entity_type, h.entity_code)
    eff_mv = _effective_market_value(h, info)
    return HoldingItem(
        id=h.id, entity_type=h.entity_type, entity_code=h.entity_code,
        entity_name=info["name"],
        market_value=decimal_to_str(eff_mv) or "0",
        quantity=decimal_to_str(h.quantity),
        latest_price=info.get("latest_price"),
        input_mode="quantity" if h.quantity is not None else "value",
        weight_pct=None,
        temperature=info["temperature"], tier=info["tier"],
        temperature_source=info["temperature_source"],
        pe_ttm=info["pe_ttm"], pb=info["pb"],
        note=h.note, added_at=h.added_at, updated_at=h.updated_at,
    )


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(holding_id: int, session: Session = Depends(db_session)):
    h = session.get(Holding, holding_id)
    if h is None:
        raise HTTPException(404, f"未找到持仓 {holding_id}")
    session.delete(h)
    session.commit()
