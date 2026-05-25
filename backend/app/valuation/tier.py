"""档位映射 + 信号方向。引用 SRS D1。"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Boundaries:
    """档位边界（百分位，0–1）。

    含义：
      pe_percentile < extreme_low_upper                                  → 极度低估
      extreme_low_upper <= pe_percentile < low_upper                     → 低估
      low_upper        <= pe_percentile < high_lower                     → 合理
      high_lower       <= pe_percentile < extreme_high_lower             → 高估
      extreme_high_lower <= pe_percentile                                → 极度高估
    """

    extreme_low_upper: Decimal
    low_upper: Decimal
    high_lower: Decimal
    extreme_high_lower: Decimal


DEFAULT_BOUNDARIES = Boundaries(
    extreme_low_upper=Decimal("0.10"),
    low_upper=Decimal("0.30"),
    high_lower=Decimal("0.70"),
    extreme_high_lower=Decimal("0.90"),
)


TIER_EXTREME_LOW = "极度低估"
TIER_LOW = "低估"
TIER_FAIR = "合理"
TIER_HIGH = "高估"
TIER_EXTREME_HIGH = "极度高估"


def tier_of(pe_percentile: Decimal | None, boundaries: Boundaries = DEFAULT_BOUNDARIES) -> str | None:
    if pe_percentile is None:
        return None
    p = pe_percentile
    if p < boundaries.extreme_low_upper:
        return TIER_EXTREME_LOW
    if p < boundaries.low_upper:
        return TIER_LOW
    if p < boundaries.high_lower:
        return TIER_FAIR
    if p < boundaries.extreme_high_lower:
        return TIER_HIGH
    return TIER_EXTREME_HIGH


_DIRECTION = {
    TIER_EXTREME_LOW: "STRONG_BUY",
    TIER_LOW: "BUY",
    TIER_FAIR: None,
    TIER_HIGH: "SELL",
    TIER_EXTREME_HIGH: "STRONG_SELL",
}


def direction_for_tier(tier: str | None) -> str | None:
    if tier is None:
        return None
    return _DIRECTION.get(tier)
