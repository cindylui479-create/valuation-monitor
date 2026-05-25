from decimal import Decimal

from app.valuation.percentile import percentile_of


def D(s: str) -> Decimal:
    return Decimal(s)


def test_empty_series_returns_none():
    assert percentile_of(D("1"), []) is None


def test_minimum_value_percentile_is_zero():
    series = sorted([D("1"), D("2"), D("3"), D("4")])
    assert percentile_of(D("1"), series) == Decimal("0.125")  # mid-rank: (0+1)/2 / 4


def test_maximum_value_percentile():
    series = sorted([D("1"), D("2"), D("3"), D("4")])
    # value=4 → lo=3, hi=4 → rank=3.5 → 3.5/4 = 0.875
    assert percentile_of(D("4"), series) == Decimal("0.875")


def test_ties_midrank():
    """相同值取中位法：4个值相同时百分位居中。"""
    series = sorted([D("5"), D("5"), D("5"), D("5")])
    # lo=0, hi=4 → rank=2 → 2/4 = 0.5
    assert percentile_of(D("5"), series) == Decimal("0.5")


def test_middle_value():
    series = sorted([D("1"), D("2"), D("3"), D("4"), D("5")])
    # value=3 → lo=2, hi=3 → rank=2.5 → 2.5/5 = 0.5
    assert percentile_of(D("3"), series) == Decimal("0.5")


def test_value_between_existing():
    series = sorted([D("1"), D("2"), D("4"), D("5")])
    # value=3 → lo=hi=2 → rank=2 → 2/4 = 0.5
    assert percentile_of(D("3"), series) == Decimal("0.5")
