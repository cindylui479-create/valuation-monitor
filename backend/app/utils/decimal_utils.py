from __future__ import annotations

import math
from decimal import Decimal


def to_decimal(value: object) -> Decimal | None:
    """容错的 Decimal 转换：None / NaN / 空字符串 → None。"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return Decimal(str(value))
    if isinstance(value, int):
        return Decimal(value)
    s = str(value).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def decimal_to_str(d: Decimal | None) -> str | None:
    if d is None:
        return None
    return format(d, "f")
