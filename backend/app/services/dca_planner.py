"""定投规划器（SRS FR-5 + D6 方案 A）。

每日批处理 + 计划 CRUD 后调用：
1. 找出该指数对应市场的全部启用计划
2. 计算未来 N 天内每个理论触发日
3. 顺延到下一个交易日（非交易日跳到下一开盘）
4. 用 latest 10y valuation 的 tier（应用个性化阈值）算 multiplier
5. upsert DCAExecution（status=PENDING）
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models import DCAExecution, DCAPlan, IndexMeta, Market
from app.repositories import dca_repo, index_repo, valuation_repo
from app.services.boundaries_service import boundaries_for
from app.trading_calendar.utils import next_trading_day_inclusive
from app.utils.logging import get_logger
from app.utils.time_utils import now_iso
from app.valuation import (
    TIER_EXTREME_HIGH,
    TIER_EXTREME_LOW,
    TIER_FAIR,
    TIER_HIGH,
    TIER_LOW,
    tier_of,
)

log = get_logger("dca_planner")

# 默认预估窗口：未来 30 天内的触发日都生成 PENDING；批处理每日刷新
LOOKAHEAD_DAYS = 30


def compute_multiplier(tier: str | None) -> Decimal:
    """D6 方案 A：档位 → 乘数；联动通过 boundaries_for 已在 tier 计算中生效。"""
    return {
        TIER_EXTREME_LOW: Decimal("2.0"),
        TIER_LOW: Decimal("2.0"),
        TIER_FAIR: Decimal("1.0"),
        TIER_HIGH: Decimal("0.5"),
        TIER_EXTREME_HIGH: Decimal("0.0"),
    }.get(tier or "", Decimal("1.0"))


def upcoming_scheduled_dates(plan: DCAPlan, from_: date, lookahead_days: int) -> list[date]:
    """根据计划频率，返回从 from_ 起 lookahead_days 内的理论触发日（未顺延）。"""
    out: list[date] = []
    start = date.fromisoformat(plan.start_date)
    end = from_ + timedelta(days=lookahead_days)

    if plan.frequency == "WEEKLY":
        # day_of_period 1-7 = 周一到周日
        target_weekday = plan.day_of_period - 1
        # 从 from_ 开始找下一个 target weekday，逐步前进 7 天
        d = max(from_, start)
        # 调整到第一个 target weekday
        delta_to_target = (target_weekday - d.weekday()) % 7
        d = d + timedelta(days=delta_to_target)
        while d <= end:
            if d >= start:
                out.append(d)
            d += timedelta(days=7)
    elif plan.frequency == "BIWEEKLY":
        target_weekday = plan.day_of_period - 1
        d = max(from_, start)
        delta_to_target = (target_weekday - d.weekday()) % 7
        d = d + timedelta(days=delta_to_target)
        # 对齐到 start_date 的 2 周节奏
        aligned_delta = (d - start).days
        if aligned_delta % 14 != 0:
            d = d + timedelta(days=(14 - aligned_delta % 14))
        while d <= end:
            if d >= start:
                out.append(d)
            d += timedelta(days=14)
    elif plan.frequency == "MONTHLY":
        # day_of_period 1-28：每月该日
        d = max(from_, start).replace(day=1)
        target_day = plan.day_of_period
        while d <= end:
            try:
                trigger = d.replace(day=target_day)
            except ValueError:
                trigger = d.replace(day=28)
            if from_ <= trigger <= end and trigger >= start:
                out.append(trigger)
            d = d + relativedelta(months=1)
    else:
        log.warning("dca.unknown_frequency", plan_id=plan.id, freq=plan.frequency)
    return out


def refresh_executions_for_market(session: Session, market_code: str, today: date) -> int:
    """对该市场所有启用计划生成未来 LOOKAHEAD_DAYS 内的 DCAExecution。"""
    n = 0
    market = session.query(Market).filter_by(code=market_code).one_or_none()
    if market is None:
        return 0
    for plan, idx, _fund in dca_repo.list_plans(session, enabled_only=True):
        if idx.market_id != market.id:
            continue
        n += _generate_for_plan(session, plan, idx, market_code, today)
    return n


def _generate_for_plan(session: Session, plan: DCAPlan, idx: IndexMeta, market_code: str, today: date) -> int:
    n_new = 0
    for scheduled in upcoming_scheduled_dates(plan, today, LOOKAHEAD_DAYS):
        try:
            actual = next_trading_day_inclusive(session, market_code, scheduled)
        except ValueError:
            log.warning("dca.no_trading_day", plan_id=plan.id, scheduled=scheduled.isoformat())
            continue

        v = valuation_repo.latest(session, idx.id, window="10y")
        if v is not None and v.pe_percentile is not None:
            boundaries = boundaries_for(session, idx.id)
            tier = tier_of(v.pe_percentile, boundaries) or TIER_FAIR
            temperature = v.temperature or Decimal(0)
        else:
            # 历史不足：保守按"合理"档位 (1×) 提醒，仍提示
            tier = TIER_FAIR
            temperature = Decimal(0)

        multiplier = compute_multiplier(tier)
        adjusted = (plan.amount * multiplier).quantize(Decimal("0.01"))

        is_new, _ = dca_repo.upsert_execution(
            session,
            DCAExecution(
                plan_id=plan.id,
                scheduled_date=scheduled.isoformat(),
                actual_date=actual.isoformat(),
                base_amount=plan.amount,
                adjusted_amount=adjusted,
                multiplier=multiplier,
                tier_at_decision=tier,
                temperature=temperature,
                status="PENDING",
                generated_at=now_iso(),
            ),
        )
        if is_new:
            n_new += 1
    return n_new


def refresh_executions_for_plan(session: Session, plan: DCAPlan, today: date | None = None) -> int:
    """单个计划立刻刷新（创建/更新计划后调用）。"""
    today = today or date.today()
    idx = session.get(IndexMeta, plan.index_id)
    if idx is None:
        return 0
    market = session.get(Market, idx.market_id)
    if market is None:
        return 0
    return _generate_for_plan(session, plan, idx, market.code, today)
