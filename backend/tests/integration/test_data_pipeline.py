"""集成测试：用 FakeAdapter 跑通整条管线 —— 拉取 → 入库 → 重算分位 → 审计日志。"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.adapters.base import DataSourceAdapter, QuoteRow
from app.adapters.registry import AdapterRegistry
from app.models import DataAudit, IndexMeta, IndexQuote, Market, Valuation
from app.services import data_pipeline


class FakeAdapter(DataSourceAdapter):
    name = "fake"
    supported_markets = ("A",)

    def __init__(self) -> None:
        self.rows_by_code: dict[str, list[QuoteRow]] = {}

    def add_row(self, code: str, date_str: str, close: float, pe: float, pb: float, dy: float) -> None:
        self.rows_by_code.setdefault(code, []).append(
            QuoteRow(
                index_code=code,
                date=date_str,
                close=Decimal(str(close)),
                pe_ttm=Decimal(str(pe)),
                pb=Decimal(str(pb)),
                dividend_yield=Decimal(str(dy)),
                source="fake",
            )
        )

    def fetch_quotes(self, index_codes, start, end):
        for code in index_codes:
            for r in self.rows_by_code.get(code, []):
                if start.isoformat() <= r.date <= end.isoformat():
                    yield r

    def fetch_calendar(self, market, year):
        return []


@pytest.fixture
def seed_a_market(session):
    m = Market(code="A", name="A 股", currency="CNY", tz="Asia/Shanghai")
    session.add(m)
    session.flush()
    idx = IndexMeta(
        code="000300.SH",
        name="沪深300",
        market_id=m.id,
        category="宽基",
        data_source="fake",
        history_start_date="2005-04-08",
        enabled=True,
    )
    session.add(idx)
    session.commit()
    return idx


def test_pipeline_ingests_and_computes(session, seed_a_market, monkeypatch):
    fake = FakeAdapter()
    # 注入 30 天数据，PE 在 10-14 之间
    today = date.today()
    for i in range(60):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:  # 跳过周末，符合 A 股
            continue
        fake.add_row("000300.SH", d.isoformat(), close=3500 + i, pe=12 + (i % 3), pb=1.5, dy=0.03)

    registry = AdapterRegistry()
    registry._by_name["fake"] = fake
    registry._fallback_by_market["A"] = [fake]

    monkeypatch.setattr(data_pipeline, "get_registry", lambda: registry)

    result = data_pipeline.run_for_market(session, market="A", target_date=today)

    assert result.success is True
    assert result.indices_processed == 1
    assert result.rows_upserted > 0

    quotes = session.scalars(select(IndexQuote)).all()
    assert len(quotes) > 0

    valuations = session.scalars(select(Valuation).where(Valuation.window == "10y")).all()
    assert len(valuations) > 0


def test_audit_log_written_on_overwrite(session, seed_a_market, monkeypatch):
    fake = FakeAdapter()
    today = date.today()
    fake.add_row("000300.SH", (today - timedelta(days=5)).isoformat(),
                 close=3500, pe=12, pb=1.5, dy=0.03)

    registry = AdapterRegistry()
    registry._by_name["fake"] = fake
    registry._fallback_by_market["A"] = [fake]
    monkeypatch.setattr(data_pipeline, "get_registry", lambda: registry)

    data_pipeline.run_for_market(session, market="A", target_date=today)

    # 第二次运行：PE 改为 13，应产生 audit log
    fake.rows_by_code["000300.SH"][0] = QuoteRow(
        index_code="000300.SH",
        date=(today - timedelta(days=5)).isoformat(),
        close=Decimal("3500"),
        pe_ttm=Decimal("13"),
        pb=Decimal("1.5"),
        dividend_yield=Decimal("0.03"),
        source="fake",
    )
    data_pipeline.run_for_market(session, market="A", target_date=today)

    audits = session.scalars(select(DataAudit).where(DataAudit.field == "pe_ttm")).all()
    assert len(audits) >= 1
    assert audits[0].old_value is not None
    assert audits[0].new_value is not None
