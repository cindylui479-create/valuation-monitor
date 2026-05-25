"""百分位计算（含相同值取中位法）。

引用 SRS §FR-3 与 DESIGN §6.1。
"""
from __future__ import annotations

import bisect
from decimal import Decimal


def percentile_of(value: Decimal | float, sorted_series: list[Decimal]) -> Decimal | None:
    """返回 value 在升序序列中的百分位（0.0–1.0）。

    含相同值时取中位法：(left_rank + right_rank) / 2 / len。
    空序列返回 None。
    """
    if not sorted_series:
        return None
    v = Decimal(value) if not isinstance(value, Decimal) else value
    lo = bisect.bisect_left(sorted_series, v)
    hi = bisect.bisect_right(sorted_series, v)
    rank = Decimal(lo + hi) / Decimal(2)
    return rank / Decimal(len(sorted_series))
