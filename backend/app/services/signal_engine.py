"""信号引擎（SRS FR-5 + D1 / D6 / R7）。

每日批处理后，对每个指数：
1. 用 valuation 表的 10y 窗口的 pe_percentile 做判定（R7：< 250 个数据点的不出信号）
2. 应用该指数的个性化阈值（D6 方案 A：阈值与定投联动）
3. 输出方向：STRONG_BUY / BUY / SELL / STRONG_SELL（合理档位不出信号）
4. has_enough_history（实际 quotes ≥ 5 年）方可出信号
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Signal
from app.repositories import index_repo, signal_repo, valuation_repo
from app.services.boundaries_service import boundaries_for
from app.services.valuation_service import has_enough_history
from app.utils.logging import get_logger
from app.utils.time_utils import now_iso
from app.valuation import direction_for_tier, tier_of

log = get_logger("signal_engine")


def generate_signals_for(
    session: Session, market_code: str, date_: str, source: str = "lg",
) -> int:
    """SRS R10：按 source 出信号。LG 与 CSI 口径独立出，DB 中信号表不区分 source（覆盖式）。

    Watchlist/前端切换偏好时调用 regenerate_signals_for(... source='csi')
    可立即重新生成；下次批处理也会按用户偏好出。
    """
    indices = index_repo.list_indices(session, market_code=market_code)
    n = 0
    for idx in indices:
        if not has_enough_history(session, idx, min_years=5):
            continue
        v_with = valuation_repo.latest_with_fallback(
            session, idx.id, window="10y", preferred=source
        )
        v = v_with[0] if v_with else None
        if v is None or v.date != date_ or v.pe_percentile is None:
            continue

        # D6 联动方案 A：用户覆盖阈值后档位随之移动
        boundaries = boundaries_for(session, idx.id)
        tier = tier_of(v.pe_percentile, boundaries)
        direction = direction_for_tier(tier)
        if direction is None:
            # 合理档位：清理该指数当日可能存在的旧信号（同 source）
            signal_repo.delete_for_date(session, idx.id, date_, source=source)
            continue

        signal_repo.upsert(
            session,
            Signal(
                index_id=idx.id,
                date=date_,
                source=source,
                direction=direction,
                tier=tier,
                temperature=v.temperature,
                generated_at=now_iso(),
            ),
        )
        n += 1
    return n
