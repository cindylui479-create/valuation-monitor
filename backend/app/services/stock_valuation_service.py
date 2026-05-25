"""SRS R12 §11.2.3：个股派生分位 + 温度计算。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Stock, StockValuation
from app.repositories import stock_repo
from app.utils.time_utils import now_iso
from app.valuation import DEFAULT_BOUNDARIES, percentile_of, tier_of
from app.valuation.anchor import temperature_from_anchor

# 与 valuation_service 一致
WINDOWS_DAYS = {"5y": 5 * 365, "10y": 10 * 365}
MIN_DATAPOINTS_FOR_PERCENTILE = 250


def _start_for_window(end_d: date, window: str) -> str | None:
    if window == "all":
        return None
    days = WINDOWS_DAYS[window]
    return (end_d - timedelta(days=days)).isoformat()


def effective_anchor(session: Session, stock: Stock) -> str:
    """覆盖优先级：StockOverride > Stock.valuation_anchor > 'PE'。"""
    ov = stock_repo.get_override(session, stock.id)
    if ov and ov.valuation_anchor:
        return ov.valuation_anchor
    return stock.valuation_anchor or "PE"


def recompute_for_stock(
    session: Session,
    stock: Stock,
    dates: list[str],
    windows: tuple[str, ...] = ("5y", "10y", "all"),
    source: str = "tushare",
) -> int:
    """对个股的 (dates × windows) 组合重算分位 + 温度。"""
    written = 0
    anchor = effective_anchor(session, stock)
    for d in dates:
        q = stock_repo.get_quote(session, stock.id, d)
        if q is None:
            continue
        end_d = date.fromisoformat(d)
        for w in windows:
            start = _start_for_window(end_d, w)
            pe_series = stock_repo.get_series_for_field(session, stock.id, "pe_ttm", start=start, end=d)
            pb_series = stock_repo.get_series_for_field(session, stock.id, "pb", start=start, end=d)
            ps_series = stock_repo.get_series_for_field(session, stock.id, "ps_ttm", start=start, end=d)
            dy_series = stock_repo.get_series_for_field(session, stock.id, "dv_ttm", start=start, end=d)

            pe_p = _percentile_safe(q.pe_ttm, pe_series)
            pb_p = _percentile_safe(q.pb, pb_series)
            ps_p = _percentile_safe(q.ps_ttm, ps_series)
            dy_p = _percentile_safe(q.dv_ttm, dy_series)

            # 温度按锚算（仅 10y 窗口；档位用相同温度映射）
            if w == "10y":
                temp = temperature_from_anchor(anchor, pe_p, pb_p, ps_p, dy_p)
                # tier_of 接受 percentile (0-1)；温度反推 percentile
                tier_pctl = temp / Decimal(100) if temp is not None else None
                tier = tier_of(tier_pctl, DEFAULT_BOUNDARIES) if tier_pctl is not None else None
            else:
                temp = None
                tier = None

            v = StockValuation(
                stock_id=stock.id, date=d, window=w, source=source, anchor=anchor,
                pe_percentile=pe_p, pb_percentile=pb_p, ps_percentile=ps_p, dy_percentile=dy_p,
                temperature=temp, tier=tier, computed_at=now_iso(),
            )
            stock_repo.upsert_valuation(session, v)
            written += 1
    return written


def _percentile_safe(value: Decimal | None, series: list[Decimal]) -> Decimal | None:
    if value is None or len(series) < MIN_DATAPOINTS_FOR_PERCENTILE:
        return None
    return percentile_of(value, sorted(series))


def data_window_note(session: Session, stock: Stock) -> str | None:
    """复用 §FR-3 R3 规则：以 stock_quote 实际可用日期为准。"""
    years = stock_repo.actual_history_years(session, stock.id)
    if years < 5:
        return "分位不可用（数据 < 5 年）"
    if years < 10:
        return f"窗口={years:.1f}年"
    return None
