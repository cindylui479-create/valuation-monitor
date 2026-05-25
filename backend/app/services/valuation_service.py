"""估值派生计算：把 IndexQuote 转为 Valuation。"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import IndexMeta, Valuation
from app.repositories import quote_repo, valuation_repo
from app.utils.time_utils import now_iso
from app.valuation import (
    DEFAULT_BOUNDARIES,
    percentile_of,
    temperature_of,
    tier_of,
)


WINDOWS_DAYS = {"5y": 5 * 365, "10y": 10 * 365}

# 分位至少需要的数据点数。低于此值视为「快照」而非历史，温度/档位/分位均不产出。
# SRS 附录 B R7：港美股目前仅最新一行有 PE-TTM 快照（来自 yfinance.Ticker.info），
# 防止「PE 序列只有 1 个值 → percentile = 0.5 → 温度 50（合理）」的伪信号。
MIN_DATAPOINTS_FOR_PERCENTILE = 250  # ≈ 1 年交易日


def _start_for_window(end_d: date, window: str) -> str | None:
    if window == "all":
        return None
    days = WINDOWS_DAYS[window]
    return (end_d - timedelta(days=days)).isoformat()


def recompute_for_index(
    session: Session,
    index: IndexMeta,
    dates: list[str],
    windows: tuple[str, ...] = ("5y", "10y", "all"),
) -> int:  # noqa: PLR0912
    # noqa above: 双口径 + 双窗口 fallback 让分支多一些，整体可读
    """SRS R10：对给定 index 在 dates 列表上重算指定 windows 的派生分位。

    两个口径分别计算并存储：
      - source='lg': 用 IndexQuote.pe_ttm / pb（主源；LG 为主）
      - source='csi': 用 IndexQuote.pe_ttm_csi / pb_csi（仅 Tushare 覆盖的指数有）
    """
    written = 0
    for d in dates:
        q = quote_repo.get_quote(session, index.id, d)
        if q is None:
            continue
        end_d = date.fromisoformat(d)
        for w in windows:
            start = _start_for_window(end_d, w)

            # LG 口径（默认主源）
            if q.pe_ttm is not None:
                pe_series = quote_repo.get_series_for_field(
                    session, index.id, "pe_ttm", start=start, end=d
                )
                pb_series = quote_repo.get_series_for_field(
                    session, index.id, "pb", start=start, end=d
                )
                written += _compute_one(
                    session, index, d, w, "lg",
                    q.pe_ttm, q.pb, q.dividend_yield,
                    pe_series, pb_series,
                )

            # CSI 口径（仅 6 只 Tushare 覆盖的指数有数据）
            if q.pe_ttm_csi is not None:
                pe_series_csi = quote_repo.get_series_for_field(
                    session, index.id, "pe_ttm_csi", start=start, end=d
                )
                pb_series_csi = quote_repo.get_series_for_field(
                    session, index.id, "pb_csi", start=start, end=d
                )
                written += _compute_one(
                    session, index, d, w, "csi",
                    q.pe_ttm_csi, q.pb_csi, q.dividend_yield,
                    pe_series_csi, pb_series_csi,
                )
    return written


def _compute_one(
    session, index, d, window, source,
    pe_value, pb_value, dy_value,
    pe_series, pb_series,
) -> int:
    """计算单源单日单窗口的分位行。

    温度计算（双窗口 10y + all）：
      1) 默认走 PE：温度 = pe_percentile × 100，temperature_source = pe_<window>
      2) PE 不足时（< 250 数据点）fallback 到 close 价格百分位：
         温度 = close_percentile × 100，temperature_source = price_<window>
         （与基金 NAV 自比同思路；UI 必须 ⚠ 标注）
      3) close 也不足时温度 None
    """
    start = _start_for_window(date.fromisoformat(d), window)
    dy_series = quote_repo.get_series_for_field(
        session, index.id, "dividend_yield", start=start, end=d,
    )
    close_series = quote_repo.get_series_for_field(
        session, index.id, "close", start=start, end=d,
    )

    pe_p = (
        percentile_of(pe_value, sorted(pe_series))
        if len(pe_series) >= MIN_DATAPOINTS_FOR_PERCENTILE
        else None
    )
    pb_p = (
        percentile_of(pb_value, sorted(pb_series))
        if pb_value is not None and len(pb_series) >= MIN_DATAPOINTS_FOR_PERCENTILE
        else None
    )
    dy_p = (
        percentile_of(dy_value, sorted(dy_series))
        if dy_value is not None and len(dy_series) >= MIN_DATAPOINTS_FOR_PERCENTILE
        else None
    )
    close_p = None
    if len(close_series) >= MIN_DATAPOINTS_FOR_PERCENTILE:
        # 当日 close 来自 quote（不在参数里），用 _series 最后一个元素 not safe；
        # 改为查 quote
        q = quote_repo.get_quote(session, index.id, d)
        if q is not None:
            close_p = percentile_of(q.close, sorted(close_series))

    # 只在 10y / all 窗口算温度；5y 仅用于浏览
    temp = None
    tier = None
    temp_source = None
    if window in ("10y", "all"):
        if pe_p is not None:
            temp = temperature_of(pe_p)
            tier = tier_of(pe_p, DEFAULT_BOUNDARIES)
            temp_source = f"pe_{window}"
        elif close_p is not None:
            # fallback：价格百分位 → 温度
            temp = temperature_of(close_p)
            tier = tier_of(close_p, DEFAULT_BOUNDARIES)
            temp_source = f"price_{window}"

    v = Valuation(
        index_id=index.id,
        date=d,
        window=window,
        source=source,
        pe_percentile=pe_p,
        pb_percentile=pb_p,
        dy_percentile=dy_p,
        close_percentile=close_p,
        temperature=temp,
        tier=tier,
        temperature_source=temp_source,
        computed_at=now_iso(),
    )
    valuation_repo.upsert_valuation(session, v)
    return 1


def actual_history_years(session: Session, index: IndexMeta) -> float:
    """以 index_quote 表实际可用日期范围为准（SRS 附录 B R3）。

    返回可用历史的年数；表中无记录时返回 0。
    """
    from sqlalchemy import func, select

    from app.models import IndexQuote

    row = session.scalar(
        select(func.min(IndexQuote.date)).where(IndexQuote.index_id == index.id)
    )
    if row is None:
        return 0.0
    start = date.fromisoformat(row)
    return (date.today() - start).days / 365.25


def has_enough_history(session: Session, index: IndexMeta, min_years: int = 5) -> bool:
    """返回 True 时该指数可生成信号 / 绑定定投。

    判定口径：实际 index_quote 可用数据 ≥ min_years 年（SRS 附录 B R3）。
    """
    return actual_history_years(session, index) >= min_years


def data_window_note(session: Session, index: IndexMeta) -> str | None:
    """5–10 年角标 / <5 年置灰 提示文案。

    判定口径：以 index_quote 实际可用日期范围为准（SRS 附录 B R3）。
    """
    years = actual_history_years(session, index)
    if years < 5:
        return "分位不可用（数据 < 5 年）"
    if years < 10:
        return f"窗口={years:.1f}年"
    return None
