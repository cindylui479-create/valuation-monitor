"""SRS v1.3.0 I：再平衡建议（贪心算法）。

输入：当前持仓 + 目标加权温度
输出：建议的"增加/减少哪些持仓多少元"清单

策略（贪心）：
- 若 target < current：需降温 → 减仓温度高于 target 的标的 + 加仓温度低于 target 的标的
- 若 target > current：需升温 → 反之

算法（简化）：
1. 把持仓按温度排序
2. 若降温，从温度最高的开始等比例减仓，加到温度最低的标的；每轮算新组合温度
3. 满足 |new_temp - target| < tolerance 时停止
4. 若不可达（如所有持仓温度都比 target 高，且无空标的池），返回最优可达点

为避免复杂，本 MVP 只在现有持仓内做权重再分配（不引入新标的）。
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


class RebalanceSuggestRequest(BaseModel):
    target_temperature: float = Field(..., ge=0, le=100)
    tolerance: float = Field(default=2.0, ge=0.1, le=10)


class HoldingAdjustment(BaseModel):
    entity_type: str
    entity_code: str
    entity_name: str
    current_mv: str
    current_temp: str
    suggested_mv: str
    delta_mv: str               # 正数 = 加仓；负数 = 减仓
    direction: str              # 'ADD' / 'REDUCE' / 'HOLD'


class RebalanceSuggestResponse(BaseModel):
    feasible: bool
    current_temp: str | None
    target_temp: str
    projected_temp: str | None
    total_mv: str
    adjustments: list[HoldingAdjustment]
    notes: list[str]


def _weighted_temp(items: list[tuple[Decimal, Decimal]]) -> Decimal | None:
    """[(mv, temp), ...] → 加权平均温度。"""
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

    # 解析每条持仓：拿 mv + temp + name
    rows: list[dict] = []
    total_mv = Decimal(0)
    for h in holdings:
        info = _resolve_entity(session, h.entity_type, h.entity_code)
        if info["temperature"] is None:
            continue  # 无温度的持仓不参与再平衡
        mv = _effective_market_value(h, info)
        rows.append({
            "h": h,
            "name": info["name"] or h.entity_code,
            "mv": mv,
            "temp": Decimal(info["temperature"]),
        })
        total_mv += mv

    if not rows:
        raise HTTPException(400, "所有持仓均无温度数据，无法再平衡")

    target = Decimal(str(body.target_temperature))
    tol = Decimal(str(body.tolerance))

    cur_temp = _weighted_temp([(r["mv"], r["temp"]) for r in rows])
    notes: list[str] = []

    if cur_temp is None:
        raise HTTPException(400, "当前组合温度无法计算")

    # 如果已在容差内，无需调整
    if abs(cur_temp - target) <= tol:
        notes.append(f"组合温度 {float(cur_temp):.1f} 已在目标 {float(target):.1f}±{float(tol)} 范围内")
        return RebalanceSuggestResponse(
            feasible=True,
            current_temp=decimal_to_str(cur_temp),
            target_temp=decimal_to_str(target),
            projected_temp=decimal_to_str(cur_temp),
            total_mv=decimal_to_str(total_mv) or "0",
            adjustments=[],
            notes=notes,
        )

    # 把每条按温度排序：升温时把"温度低的"加权重；降温时把"温度高的"减权重
    rows_sorted = sorted(rows, key=lambda r: r["temp"])
    low_temp = rows_sorted[0]["temp"]
    high_temp = rows_sorted[-1]["temp"]
    if target < low_temp - tol:
        notes.append(f"目标温度 {float(target):.1f} 低于持仓里最低温度 {float(low_temp):.1f}，"
                     f"仅靠现有持仓不可达。")
        return RebalanceSuggestResponse(
            feasible=False, current_temp=decimal_to_str(cur_temp),
            target_temp=decimal_to_str(target),
            projected_temp=decimal_to_str(low_temp),
            total_mv=decimal_to_str(total_mv) or "0",
            adjustments=[], notes=notes,
        )
    if target > high_temp + tol:
        notes.append(f"目标温度 {float(target):.1f} 高于持仓里最高温度 {float(high_temp):.1f}，"
                     f"仅靠现有持仓不可达。")
        return RebalanceSuggestResponse(
            feasible=False, current_temp=decimal_to_str(cur_temp),
            target_temp=decimal_to_str(target),
            projected_temp=decimal_to_str(high_temp),
            total_mv=decimal_to_str(total_mv) or "0",
            adjustments=[], notes=notes,
        )

    # 求新权重 w_i 满足 Σ w_i = 1, Σ w_i × temp_i = target
    # 简化：双标的 mix（最低温度 + 最高温度），其余保持当前权重
    # → 使 (1-α) × cur_other + α × (w_low × low + w_high × high) ≈ target
    # 更简化：用线性组合：把"高于 target 的标的权重"全部均匀减少 X，
    # 把"低于 target 的标的权重"按比例加 X。
    # 解 X 用一次方程：
    #   new_temp = (Σ_low (mv_i + add_i) × temp_i + Σ_high (mv_i - cut_i) × temp_i) / total_mv = target
    # 其中 add_i / cut_i 等比例分配，Σ add = Σ cut = total_delta

    # 解：
    # Σ_low mv × temp + Σ_high mv × temp = total_mv × cur_temp
    # 若 Σ add_i × temp_low_avg = Σ cut_i × temp_high_avg + (target - cur) × total_mv
    # 简化用单一变量 X = total_delta：
    #   ΔT = X × (avg_low_temp - avg_high_temp) / total_mv
    # → target - cur = X × (avg_low_temp - avg_high_temp) / total_mv
    # → X = (target - cur) × total_mv / (avg_low_temp - avg_high_temp)
    lows = [r for r in rows if r["temp"] < target]
    highs = [r for r in rows if r["temp"] > target]
    if not lows or not highs:
        notes.append("所有持仓温度都在目标同侧（要么全高于要么全低于目标），仅靠现有持仓不可达。")
        return RebalanceSuggestResponse(
            feasible=False, current_temp=decimal_to_str(cur_temp),
            target_temp=decimal_to_str(target),
            projected_temp=decimal_to_str(cur_temp),
            total_mv=decimal_to_str(total_mv) or "0",
            adjustments=[], notes=notes,
        )

    sum_low_mv = sum(r["mv"] for r in lows)
    sum_high_mv = sum(r["mv"] for r in highs)
    avg_low_temp = sum(r["mv"] * r["temp"] for r in lows) / sum_low_mv
    avg_high_temp = sum(r["mv"] * r["temp"] for r in highs) / sum_high_mv

    denom = avg_low_temp - avg_high_temp
    if abs(denom) < Decimal("0.01"):
        notes.append("低端与高端温度差距过小，无法计算调整量。")
        return RebalanceSuggestResponse(
            feasible=False, current_temp=decimal_to_str(cur_temp),
            target_temp=decimal_to_str(target), projected_temp=decimal_to_str(cur_temp),
            total_mv=decimal_to_str(total_mv) or "0",
            adjustments=[], notes=notes,
        )

    # X = 调整量（正数表示 low 端加 X，high 端减 X）
    x = (target - cur_temp) * total_mv / denom
    # 不能超过 high 端总 mv（不能减仓到负）
    if x > sum_high_mv * Decimal("0.95"):
        x = sum_high_mv * Decimal("0.95")  # 最多减仓 95%
        notes.append(f"为达目标需减仓超过 95%，已限制到上限。projected_temp 可能与 target 有偏差。")
    if -x > sum_low_mv * Decimal("0.95"):
        x = -sum_low_mv * Decimal("0.95")
        notes.append(f"为达目标需将低端减仓超过 95%，已限制。")

    # 把 X 按 mv 比例分配
    adjustments: list[HoldingAdjustment] = []
    for r in rows:
        if r["temp"] < target:
            add = x * r["mv"] / sum_low_mv
            new_mv = r["mv"] + add
            delta = add
        elif r["temp"] > target:
            cut = x * r["mv"] / sum_high_mv
            new_mv = r["mv"] - cut
            delta = -cut
        else:
            new_mv = r["mv"]
            delta = Decimal(0)
        direction = "ADD" if delta > 1 else ("REDUCE" if delta < -1 else "HOLD")
        adjustments.append(HoldingAdjustment(
            entity_type=r["h"].entity_type,
            entity_code=r["h"].entity_code,
            entity_name=r["name"],
            current_mv=decimal_to_str(r["mv"]) or "0",
            current_temp=decimal_to_str(r["temp"]) or "0",
            suggested_mv=decimal_to_str(new_mv) or "0",
            delta_mv=decimal_to_str(delta) or "0",
            direction=direction,
        ))

    projected_temp = _weighted_temp([
        (Decimal(adj.suggested_mv), Decimal(adj.current_temp))
        for adj in adjustments
    ])

    # 排序：调整量大的在前
    adjustments.sort(key=lambda a: -abs(float(a.delta_mv)))

    return RebalanceSuggestResponse(
        feasible=True,
        current_temp=decimal_to_str(cur_temp),
        target_temp=decimal_to_str(target),
        projected_temp=decimal_to_str(projected_temp) if projected_temp else None,
        total_mv=decimal_to_str(total_mv) or "0",
        adjustments=adjustments,
        notes=notes,
    )
