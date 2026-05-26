"""SRS v1.3.1 I-fix：再平衡建议（纯逆向模式，"低买高卖"）。

逻辑（不再求"组合温度 = X"，机械求解会反直觉）：
  1. 把当前持仓按温度分三桶：
     HIGH 高估 (温度 > 70)
     LOW  低估 (温度 < 30)
     MID  合理 (30 ≤ 温度 ≤ 70)
  2. 对每个 HIGH 持仓减仓 reduce_pct（默认 30%）
  3. 释放的资金按现有 LOW 桶各持仓的 mv 比例加仓
  4. MID 桶保持不变
  5. 输出"组合温度 X → Y"作为效果摘要

边界：
- 无 HIGH 持仓：组合已无可减仓的高估标的；不动
- 无 LOW 持仓：组合无低估标的可加仓；建议持现金或人工挑标的
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.holdings import _effective_market_value, _resolve_entity
from app.deps import db_session
from app.models import Holding
from app.utils.decimal_utils import decimal_to_str

router = APIRouter()


# 默认档位（与 SRS D1 对齐）
HIGH_THRESHOLD = Decimal(70)
LOW_THRESHOLD = Decimal(30)


class RebalanceSuggestRequest(BaseModel):
    reduce_pct: float = Field(default=0.30, ge=0.05, le=0.95,
                              description="对每个高估持仓减仓的比例（0.30 = 减仓 30%）")


class HoldingAdjustment(BaseModel):
    entity_type: str
    entity_code: str
    entity_name: str
    current_mv: str
    current_temp: str
    tier: str | None
    suggested_mv: str
    delta_mv: str           # 正数 = 加仓；负数 = 减仓
    direction: str          # 'ADD' / 'REDUCE' / 'HOLD'
    bucket: str             # HIGH / LOW / MID


class RebalanceSuggestResponse(BaseModel):
    feasible: bool
    reduce_pct: str
    current_temp: str | None
    projected_temp: str | None
    total_mv: str
    total_released: str      # 高估桶减仓总额（= 低估桶加仓总额）
    n_high: int
    n_low: int
    n_mid: int
    adjustments: list[HoldingAdjustment]
    notes: list[str]


def _weighted_temp(items: list[tuple[Decimal, Decimal]]) -> Decimal | None:
    total = sum(mv for mv, _ in items)
    if total == 0:
        return None
    return sum(mv * t for mv, t in items) / total


@router.post("/holdings/rebalance-suggest", response_model=RebalanceSuggestResponse)
def rebalance_suggest(
    body: RebalanceSuggestRequest,
    session: Session = Depends(db_session),
) -> RebalanceSuggestResponse:
    holdings = list(session.scalars(select(Holding).order_by(Holding.id)))
    if not holdings:
        raise HTTPException(400, "无持仓数据")

    rows: list[dict] = []
    total_mv = Decimal(0)
    for h in holdings:
        info = _resolve_entity(session, h.entity_type, h.entity_code)
        if info["temperature"] is None:
            continue
        mv = _effective_market_value(h, info)
        rows.append({
            "h": h,
            "name": info["name"] or h.entity_code,
            "mv": mv,
            "temp": Decimal(info["temperature"]),
            "tier": info["tier"],
        })
        total_mv += mv

    if not rows:
        raise HTTPException(400, "所有持仓均无温度数据")

    reduce_pct = Decimal(str(body.reduce_pct))
    cur_temp = _weighted_temp([(r["mv"], r["temp"]) for r in rows])
    notes: list[str] = []

    # 分三桶
    high = [r for r in rows if r["temp"] > HIGH_THRESHOLD]
    low = [r for r in rows if r["temp"] < LOW_THRESHOLD]
    mid = [r for r in rows if LOW_THRESHOLD <= r["temp"] <= HIGH_THRESHOLD]

    feasible = True
    adjustments: list[HoldingAdjustment] = []
    total_released = Decimal(0)

    if not high and not low:
        notes.append(
            "组合无温度 > 70 的高估持仓，也无温度 < 30 的低估持仓 — "
            "整体温度处于合理区间，无需再平衡。"
        )
        feasible = False
    elif not high:
        notes.append("组合无温度 > 70 的高估持仓，无可减仓的资金 — 整体偏低估，建议持有。")
        feasible = False
    elif not low:
        notes.append(
            f"组合无温度 < 30 的低估持仓 — 减仓高估部分释放的 ¥{float(sum(r['mv'] for r in high) * reduce_pct):,.0f} "
            f"建议保留为现金，等待新的低估机会。"
        )
        for r in high:
            cut = r["mv"] * reduce_pct
            adjustments.append(HoldingAdjustment(
                entity_type=r["h"].entity_type, entity_code=r["h"].entity_code,
                entity_name=r["name"],
                current_mv=decimal_to_str(r["mv"]) or "0",
                current_temp=decimal_to_str(r["temp"]) or "0",
                tier=r["tier"],
                suggested_mv=decimal_to_str(r["mv"] - cut) or "0",
                delta_mv=decimal_to_str(-cut) or "0",
                direction="REDUCE", bucket="HIGH",
            ))
            total_released += cut
        feasible = True

    if high and low:
        # 减仓 HIGH
        for r in high:
            cut = r["mv"] * reduce_pct
            adjustments.append(HoldingAdjustment(
                entity_type=r["h"].entity_type, entity_code=r["h"].entity_code,
                entity_name=r["name"],
                current_mv=decimal_to_str(r["mv"]) or "0",
                current_temp=decimal_to_str(r["temp"]) or "0",
                tier=r["tier"],
                suggested_mv=decimal_to_str(r["mv"] - cut) or "0",
                delta_mv=decimal_to_str(-cut) or "0",
                direction="REDUCE", bucket="HIGH",
            ))
            total_released += cut

        # 加仓 LOW（按现有 mv 比例分配）
        sum_low_mv = sum(r["mv"] for r in low)
        for r in low:
            add = (total_released * r["mv"] / sum_low_mv) if sum_low_mv > 0 else Decimal(0)
            adjustments.append(HoldingAdjustment(
                entity_type=r["h"].entity_type, entity_code=r["h"].entity_code,
                entity_name=r["name"],
                current_mv=decimal_to_str(r["mv"]) or "0",
                current_temp=decimal_to_str(r["temp"]) or "0",
                tier=r["tier"],
                suggested_mv=decimal_to_str(r["mv"] + add) or "0",
                delta_mv=decimal_to_str(add) or "0",
                direction="ADD", bucket="LOW",
            ))

    # MID 桶：保持
    for r in mid:
        adjustments.append(HoldingAdjustment(
            entity_type=r["h"].entity_type, entity_code=r["h"].entity_code,
            entity_name=r["name"],
            current_mv=decimal_to_str(r["mv"]) or "0",
            current_temp=decimal_to_str(r["temp"]) or "0",
            tier=r["tier"],
            suggested_mv=decimal_to_str(r["mv"]) or "0",
            delta_mv="0",
            direction="HOLD", bucket="MID",
        ))

    # 投影温度
    new_pairs: list[tuple[Decimal, Decimal]] = []
    for adj in adjustments:
        new_pairs.append((Decimal(adj.suggested_mv), Decimal(adj.current_temp)))
    projected_temp = _weighted_temp(new_pairs)

    # 排序：先减仓（按金额降序）、再加仓、再持有
    order_map = {"REDUCE": 0, "ADD": 1, "HOLD": 2}
    adjustments.sort(key=lambda a: (order_map[a.direction], -abs(float(a.delta_mv))))

    if feasible and high and low:
        notes.insert(0,
            f"减仓 {len(high)} 只高估持仓（温度 > {HIGH_THRESHOLD}）各 {float(reduce_pct)*100:.0f}%，"
            f"释放 ¥{float(total_released):,.0f}，"
            f"按比例加仓 {len(low)} 只低估持仓（温度 < {LOW_THRESHOLD}）。"
        )

    return RebalanceSuggestResponse(
        feasible=feasible,
        reduce_pct=decimal_to_str(reduce_pct) or "0",
        current_temp=decimal_to_str(cur_temp) if cur_temp else None,
        projected_temp=decimal_to_str(projected_temp) if projected_temp else None,
        total_mv=decimal_to_str(total_mv) or "0",
        total_released=decimal_to_str(total_released) or "0",
        n_high=len(high),
        n_low=len(low),
        n_mid=len(mid),
        adjustments=adjustments,
        notes=notes,
    )
