from decimal import Decimal

from app.valuation.temperature import temperature_of


def test_temperature_is_percentile_times_100():
    assert temperature_of(Decimal("0.235")) == Decimal("23.500")


def test_temperature_zero():
    assert temperature_of(Decimal("0")) == Decimal("0")


def test_temperature_one():
    assert temperature_of(Decimal("1")) == Decimal("100")


def test_temperature_none():
    assert temperature_of(None) is None
