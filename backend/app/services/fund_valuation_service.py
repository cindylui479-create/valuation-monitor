"""SRS R12 §11.3.1 / §11.3.3 M7-B：主动基金 NAV 历史百分位 → 温度。

公式：temperature = nav_percentile_5y × 100
含义：NAV 越接近近 5 年最高位，温度越高（"与自己比贵"）。

注意：主动基金温度仅反映 NAV 自身历史，**不反映持仓估值水位**。
UI 必须明示这一点。
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Fund, FundValuation
from app.repositories import fund_repo
from app.utils.time_utils import now_iso
from app.valuation import DEFAULT_BOUNDARIES, percentile_of, tier_of

WINDOWS_DAYS = {"5y": 5 * 365}
MIN_DATAPOINTS_FOR_PERCENTILE = 250  # ≈ 1 年


def _start_for_window(end_d: date, window: str) -> str | None:
    if window == "all":
        return None
    return (end_d - timedelta(days=WINDOWS_DAYS[window])).isoformat()


def recompute_for_fund(
    session: Session,
    fund: Fund,
    dates: list[str],
    windows: tuple[str, ...] = ("5y", "all"),
) -> int:
    """对主动基金的 (dates × windows) 重算 NAV 分位 + 温度。

    仅 ACTIVE_FUND 适用；其他基金类型直接返回 0。
    """
    if fund.fund_type != "ACTIVE_FUND":
        return 0
    written = 0
    for d in dates:
        nav_row = fund_repo.get_nav(session, fund.id, d)
        if nav_row is None:
            continue
        end_d = date.fromisoformat(d)
        for w in windows:
            start = _start_for_window(end_d, w)
            series = fund_repo.get_nav_series(session, fund.id, start=start, end=d)
            if len(series) < MIN_DATAPOINTS_FOR_PERCENTILE:
                nav_p = None
                temp = None
                tier = None
            else:
                nav_p = percentile_of(nav_row.nav, sorted(series))
                # 温度 = nav_percentile × 100；仅 5y 窗口产出温度（与 D1 一致）
                if w == "5y" and nav_p is not None:
                    temp = nav_p * Decimal(100)
                    tier = tier_of(nav_p, DEFAULT_BOUNDARIES)
                else:
                    temp = None
                    tier = None
            v = FundValuation(
                fund_id=fund.id, date=d, window=w,
                nav_percentile=nav_p, temperature=temp, tier=tier,
                computed_at=now_iso(),
            )
            fund_repo.upsert_fund_valuation(session, v)
            written += 1
    return written


def data_window_note(session: Session, fund: Fund) -> str | None:
    """主动基金的"窗口"提示。"""
    if fund.fund_type != "ACTIVE_FUND":
        return None
    years = fund_repo.actual_history_years(session, fund.id)
    if years < 1:
        return "分位不可用（NAV 数据 < 1 年）"
    if years < 5:
        return f"窗口={years:.1f}年（小于 5 年用可用最长）"
    return None
