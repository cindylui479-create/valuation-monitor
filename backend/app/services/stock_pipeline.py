"""SRS R12 §11.2.4：个股数据采集 + 入库 + 重算分位。

两种入口：
- `init_stock_history(session, stock, years=None)`：新加入自选时一次性拉上市以来全历史
- `daily_increment(session, lookback_days=30)`：每日批处理调用，仅最近 30 天
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.adapters.stock_tushare_adapter import StockTushareAdapter
from app.models import Stock
from app.repositories import stock_repo
from app.services import stock_valuation_service
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("stock_pipeline")


@dataclass
class StockIngestResult:
    code: str
    rows: int
    seconds: float
    error: str | None = None


def init_stock_history(
    session: Session, stock: Stock, *, years: int | None = None,
) -> StockIngestResult:
    """新自选个股一次性拉历史。

    years=None 时拉上市以来全历史（即从 listing_date 到今天）；
    否则从今天往前推 N 年。
    """
    t0 = time.monotonic()
    end = date.today()
    if years:
        start = end - timedelta(days=years * 365)
    elif stock.listing_date:
        try:
            start = date.fromisoformat(stock.listing_date)
        except ValueError:
            start = end - timedelta(days=10 * 365)
    else:
        start = end - timedelta(days=10 * 365)

    adapter = StockTushareAdapter()
    n_rows = 0
    try:
        for r in adapter.fetch_quotes([stock.code], start, end):
            if stock_repo.upsert_quote(session, stock.id, r, source=adapter.name):
                n_rows += 1
        session.commit()
        log.info("stock_init.ingest_done", code=stock.code, rows=n_rows,
                 start=start.isoformat(), end=end.isoformat())

        # 重算最近 30 天分位（init 后立即可看温度）
        recent = [(end - timedelta(days=i)).isoformat() for i in range(30)]
        stock_valuation_service.recompute_for_stock(session, stock, recent)
        session.commit()
        log.info("stock_init.recompute_done", code=stock.code)

        return StockIngestResult(
            code=stock.code, rows=n_rows,
            seconds=round(time.monotonic() - t0, 2),
        )
    except FetchFailure as e:
        log.error("stock_init.fetch_failed", code=stock.code, error=str(e))
        return StockIngestResult(
            code=stock.code, rows=n_rows,
            seconds=round(time.monotonic() - t0, 2),
            error=str(e),
        )


def daily_increment(session: Session, lookback_days: int = 30) -> list[StockIngestResult]:
    """每日批处理调用：所有 enabled=True 的 Stock 拉前 30 个交易日 → upsert → 重算近 30 天。"""
    stocks = stock_repo.list_stocks(session)
    if not stocks:
        return []
    end = date.today()
    start = end - timedelta(days=lookback_days)
    adapter = StockTushareAdapter()
    results: list[StockIngestResult] = []
    for s in stocks:
        t0 = time.monotonic()
        try:
            n_rows = 0
            for r in adapter.fetch_quotes([s.code], start, end):
                if stock_repo.upsert_quote(session, s.id, r, source=adapter.name):
                    n_rows += 1
            session.commit()
            recent = [(end - timedelta(days=i)).isoformat() for i in range(lookback_days)]
            stock_valuation_service.recompute_for_stock(session, s, recent)
            session.commit()
            results.append(StockIngestResult(
                code=s.code, rows=n_rows,
                seconds=round(time.monotonic() - t0, 2),
            ))
            log.info("stock_daily.ok", code=s.code, rows=n_rows)
        except FetchFailure as e:
            log.error("stock_daily.fail", code=s.code, error=str(e))
            results.append(StockIngestResult(
                code=s.code, rows=0,
                seconds=round(time.monotonic() - t0, 2),
                error=str(e),
            ))
    return results
