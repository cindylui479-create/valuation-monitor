"""历史数据初始化脚本（SRS D10）。

按市场拉取近 N 年指数行情 + 估值 + 派生分位。
首次部署执行一次；后续走 APScheduler 每日增量。

用法：
    python -m scripts.init_history --market A --years 10
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

from app.adapters import get_registry
from app.db import SessionLocal
from app.models import IndexQuote
from app.repositories import audit_repo, index_repo, quote_repo
from app.services import valuation_service
from app.utils.exceptions import DataSourceError, FetchFailure
from app.utils.logging import get_logger, setup_logging
from app.utils.time_utils import today_iso

log = get_logger("init_history")


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, choices=["A", "HK", "US"])
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--start", type=str, default=None, help="YYYY-MM-DD 覆盖 --years")
    parser.add_argument("--batch-days", type=int, default=3650)
    args = parser.parse_args()

    if args.start:
        start = date.fromisoformat(args.start)
    else:
        start = date.today() - timedelta(days=args.years * 365)
    end = date.today()

    registry = get_registry()

    with SessionLocal() as session:
        indices = index_repo.list_indices(session, market_code=args.market)
        log.info("init.start", market=args.market, indices=len(indices),
                 start=start.isoformat(), end=end.isoformat())

        for idx in indices:
            t0 = time.monotonic()
            adapters = registry.fallbacks_for_index(args.market, idx.code)
            try:
                _ingest_full(session, idx, start, end, adapters)
                session.commit()
                log.info("init.ingest_done", code=idx.code,
                         seconds=round(time.monotonic() - t0, 2))
            except DataSourceError as e:
                log.error("init.failed", code=idx.code, error=str(e))
                session.rollback()
                continue

            # SRS R10：Tushare 覆盖的指数额外拉一次 CSI 数据填 pe_ttm_csi/pb_csi
            if args.market == "A":
                t0 = time.monotonic()
                from app.services.data_pipeline import TUSHARE_CSI_COVERED
                if idx.code in TUSHARE_CSI_COVERED:
                    try:
                        from app.adapters.tushare_adapter import TushareAdapter
                        from app.repositories import quote_repo
                        ts = TushareAdapter()
                        rows = list(ts.fetch_quotes([idx.code], start, end))
                        n_csi = 0
                        for r in rows:
                            if quote_repo.update_csi_values(
                                session, idx.id, r.date, r.pe_ttm, r.pb
                            ):
                                n_csi += 1
                        session.commit()
                        log.info("init.csi_augmented", code=idx.code, count=n_csi,
                                 seconds=round(time.monotonic() - t0, 2))
                    except Exception as e:
                        log.warning("init.csi_augment_skip", code=idx.code, error=str(e)[:120])

            t0 = time.monotonic()
            recent_dates = [
                (end - timedelta(days=i)).isoformat()
                for i in range((end - start).days + 1)
            ]
            valuation_service.recompute_for_index(session, idx, recent_dates)
            session.commit()
            log.info("init.recompute_done", code=idx.code,
                     seconds=round(time.monotonic() - t0, 2))


def _ingest_full(session, idx, start, end, adapters) -> None:
    last_err: Exception | None = None
    for adp in adapters:
        try:
            rows = list(adp.fetch_quotes([idx.code], start, end))
            for r in rows:
                q = IndexQuote(
                    index_id=idx.id,
                    date=r.date,
                    close=r.close,
                    pe_ttm=r.pe_ttm,
                    pb=r.pb,
                    dividend_yield=r.dividend_yield,
                    roe=r.roe,
                    earnings_growth_3y=r.earnings_growth_3y,
                    ma50=r.ma50,
                    ma200=r.ma200,
                    northbound_60d_pct=r.northbound_60d_pct,
                    source=adp.name,
                    created_at=today_iso(),
                )
                changed, diffs = quote_repo.upsert_quote(session, q, source=adp.name)
                if changed and diffs:
                    rk = f"index_quote:{idx.code}:{r.date}"
                    for f, ov, nv in diffs:
                        audit_repo.log_change(
                            session, "index_quote", rk, f, ov, nv, adp.name
                        )
            return
        except FetchFailure as e:
            last_err = e
            continue
    raise DataSourceError(f"all adapters failed for {idx.code}: {last_err}")


if __name__ == "__main__":
    main()
