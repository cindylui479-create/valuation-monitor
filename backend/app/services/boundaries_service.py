"""个性化阈值（ThresholdOverride）→ Boundaries 解析。

集中复用：信号引擎、定投规划器、UI（通过 API）都依赖这套规则。
SRS D1：用户可以仅覆盖部分边界，未指定的回退默认。
"""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories import override_repo
from app.valuation import DEFAULT_BOUNDARIES, Boundaries


def boundaries_for(session: Session, index_id: int) -> Boundaries:
    """返回该指数最终生效的 Boundaries（自定义覆盖 + 默认回退）。"""
    ov = override_repo.get_for_index(session, index_id)
    if ov is None:
        return DEFAULT_BOUNDARIES
    payload = json.loads(ov.boundaries_json or "{}")
    return Boundaries(
        extreme_low_upper=_dec(payload.get("extreme_low_upper"), DEFAULT_BOUNDARIES.extreme_low_upper),
        low_upper=_dec(payload.get("low_upper"), DEFAULT_BOUNDARIES.low_upper),
        high_lower=_dec(payload.get("high_lower"), DEFAULT_BOUNDARIES.high_lower),
        extreme_high_lower=_dec(payload.get("extreme_high_lower"), DEFAULT_BOUNDARIES.extreme_high_lower),
    )


def _dec(v, default: Decimal) -> Decimal:
    if v is None:
        return default
    return Decimal(str(v))
