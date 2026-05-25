from decimal import Decimal

from app.valuation.tier import (
    DEFAULT_BOUNDARIES,
    Boundaries,
    direction_for_tier,
    tier_of,
)


def D(s: str) -> Decimal:
    return Decimal(s)


def test_extreme_low_strictly_below_10pct():
    assert tier_of(D("0.05"), DEFAULT_BOUNDARIES) == "极度低估"
    # SRS 明确：< 10% 极度低估；10% 起为低估
    assert tier_of(D("0.10"), DEFAULT_BOUNDARIES) == "低估"


def test_low_range():
    assert tier_of(D("0.10"), DEFAULT_BOUNDARIES) == "低估"
    assert tier_of(D("0.29"), DEFAULT_BOUNDARIES) == "低估"
    assert tier_of(D("0.30"), DEFAULT_BOUNDARIES) == "合理"


def test_fair_range():
    assert tier_of(D("0.50"), DEFAULT_BOUNDARIES) == "合理"
    assert tier_of(D("0.69"), DEFAULT_BOUNDARIES) == "合理"
    assert tier_of(D("0.70"), DEFAULT_BOUNDARIES) == "高估"


def test_high_range():
    assert tier_of(D("0.85"), DEFAULT_BOUNDARIES) == "高估"
    assert tier_of(D("0.90"), DEFAULT_BOUNDARIES) == "极度高估"


def test_extreme_high():
    assert tier_of(D("0.99"), DEFAULT_BOUNDARIES) == "极度高估"


def test_none_returns_none():
    assert tier_of(None, DEFAULT_BOUNDARIES) is None


def test_custom_boundaries():
    """D6 联动方案 A：用户覆盖边界后，加倍/减半区间随之移动。"""
    custom = Boundaries(
        extreme_low_upper=D("0.05"),
        low_upper=D("0.15"),
        high_lower=D("0.75"),
        extreme_high_lower=D("0.95"),
    )
    # 0.20 在默认边界下是"低估"（加倍），在 custom 下是"合理"（正常）
    assert tier_of(D("0.20"), DEFAULT_BOUNDARIES) == "低估"
    assert tier_of(D("0.20"), custom) == "合理"


def test_direction_mapping():
    assert direction_for_tier("极度低估") == "STRONG_BUY"
    assert direction_for_tier("低估") == "BUY"
    assert direction_for_tier("合理") is None
    assert direction_for_tier("高估") == "SELL"
    assert direction_for_tier("极度高估") == "STRONG_SELL"
    assert direction_for_tier(None) is None
