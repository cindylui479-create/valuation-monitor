"""温度计算：温度 = PE 百分位 × 100（一一映射）。"""
from __future__ import annotations

from decimal import Decimal


def temperature_of(pe_percentile: Decimal | None) -> Decimal | None:
    if pe_percentile is None:
        return None
    return pe_percentile * Decimal(100)
