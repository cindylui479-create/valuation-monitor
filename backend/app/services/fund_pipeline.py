"""SRS R12 §11.3.3 M7-B：主动基金 NAV 拉数 + 重算分位。

`init_fund_history(fund)`：新加入主动基金时一次性拉全部 NAV
`daily_increment()`：每日批处理调用，所有 ACTIVE_FUND 拉前 5 日 NAV（T+1 滞后）
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.adapters.fund_akshare_adapter import FundAkshareAdapter
from app.models import Fund
from app.repositories import fund_repo
from app.services import fund_valuation_service
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("fund_pipeline")


@dataclass
class FundIngestResult:
    code: str
    rows: int
    seconds: float
    error: str | None = None


def init_fund_history(session: Session, fund: Fund) -> FundIngestResult:
    """新加入主动基金 → 一次性拉全部 NAV 历史。"""
    t0 = time.monotonic()
    adapter = FundAkshareAdapter()
    n_rows = 0
    try:
        for point in adapter.fetch_nav_history(fund.code):
            if fund_repo.upsert_nav(session, fund.id, point.date, point.nav, point.accumulated_nav):
                n_rows += 1
        session.commit()
        log.info("fund_init.ingest_done", code=fund.code, rows=n_rows)

        # 重算最近 30 天分位
        end = date.today()
        recent = [(end - timedelta(days=i)).isoformat() for i in range(30)]
        fund_valuation_service.recompute_for_fund(session, fund, recent)
        session.commit()
        log.info("fund_init.recompute_done", code=fund.code)

        return FundIngestResult(
            code=fund.code, rows=n_rows,
            seconds=round(time.monotonic() - t0, 2),
        )
    except FetchFailure as e:
        log.error("fund_init.failed", code=fund.code, error=str(e))
        return FundIngestResult(
            code=fund.code, rows=n_rows,
            seconds=round(time.monotonic() - t0, 2),
            error=str(e),
        )


def daily_increment(session: Session, lookback_days: int = 10) -> list[FundIngestResult]:
    """每日批处理：所有 ACTIVE_FUND 拉前 N 天 NAV → upsert → 重算分位。"""
    funds = fund_repo.list_funds(session, fund_type="ACTIVE_FUND")
    if not funds:
        return []
    adapter = FundAkshareAdapter()
    results: list[FundIngestResult] = []
    end = date.today()
    for f in funds:
        t0 = time.monotonic()
        try:
            n_rows = 0
            # akshare 接口返回全历史，本地按 date 过滤近 lookback_days
            cutoff_date = (end - timedelta(days=lookback_days)).isoformat()
            for point in adapter.fetch_nav_history(f.code):
                if point.date < cutoff_date:
                    continue
                if fund_repo.upsert_nav(session, f.id, point.date, point.nav, point.accumulated_nav):
                    n_rows += 1
            session.commit()
            recent = [(end - timedelta(days=i)).isoformat() for i in range(lookback_days)]
            fund_valuation_service.recompute_for_fund(session, f, recent)
            session.commit()
            results.append(FundIngestResult(
                code=f.code, rows=n_rows,
                seconds=round(time.monotonic() - t0, 2),
            ))
            log.info("fund_daily.ok", code=f.code, rows=n_rows)
        except FetchFailure as e:
            log.error("fund_daily.fail", code=f.code, error=str(e))
            results.append(FundIngestResult(
                code=f.code, rows=0,
                seconds=round(time.monotonic() - t0, 2),
                error=str(e),
            ))
    return results
