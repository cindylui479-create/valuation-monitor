"""SRS v1.1.0 方案 A：成分股加权聚合 PE 一次性 backfill。

目标指数（Tushare index_dailybasic 不覆盖）：
  000932.SH 中证消费
  H30269.CSI 中证红利低波动
  000688.SH 科创板 50

流程：
  1) fetch_index_weights：拉 10y 成分股权重月度报告（IndexConstituent）
  2) fetch_constituent_quotes：拉每只历史成分股 10y daily_basic（IndexConstituentQuote）
     - 跳过已有数据的股票（幂等）
  3) backfill_index_pe：对每个交易日做整体法聚合 → 写 index_quote.pe_ttm

用法：
  python -m scripts.backfill_constituent_pe                # 三只都跑
  python -m scripts.backfill_constituent_pe --code 000932.SH
  python -m scripts.backfill_constituent_pe --years 5      # 缩短历史
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

from app.db import SessionLocal
from app.repositories import constituent_repo, index_repo
from app.services import constituent_fetcher, constituent_pe_service
from app.utils.logging import get_logger, setup_logging

log = get_logger("backfill_constituent")

DEFAULT_TARGETS = ["000932.SH", "H30269.CSI", "000688.SH"]


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", help="指定单只指数；否则跑全部三只")
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--skip-weights", action="store_true",
                        help="跳过 fetch_index_weights 步骤（如已拉过）")
    parser.add_argument("--skip-quotes", action="store_true",
                        help="跳过 fetch_constituent_quotes 步骤")
    parser.add_argument("--skip-aggregate", action="store_true",
                        help="跳过最终 backfill_index_pe 步骤")
    args = parser.parse_args()

    targets = [args.code] if args.code else DEFAULT_TARGETS
    end = date.today()
    start = end - timedelta(days=args.years * 365)

    with SessionLocal() as session:
        for code in targets:
            idx = index_repo.get_by_code(session, code)
            if idx is None:
                log.error("backfill.index_not_found", code=code)
                continue
            log.info("backfill.start", code=code, name=idx.name,
                     start=start.isoformat(), end=end.isoformat())

            # Step 1: 权重
            if not args.skip_weights:
                t0 = time.monotonic()
                n_w = constituent_fetcher.fetch_index_weights(
                    session, idx.id, code, start=start, end=end,
                )
                session.commit()
                log.info("backfill.weights_done", code=code, rows=n_w,
                         seconds=round(time.monotonic() - t0, 1))

            stock_codes = constituent_repo.list_distinct_stock_codes(session, idx.id)
            log.info("backfill.unique_stocks", code=code, n=len(stock_codes))

            # Step 2: 成分股 daily_basic
            if not args.skip_quotes:
                t0 = time.monotonic()
                n_s, n_r = constituent_fetcher.fetch_constituent_quotes(
                    session, stock_codes, start=start, end=end, skip_existing=True,
                )
                log.info("backfill.quotes_done", code=code,
                         stocks_processed=n_s, rows_upserted=n_r,
                         seconds=round(time.monotonic() - t0, 1))

            # Step 3: 聚合 PE → 写 index_quote
            if not args.skip_aggregate:
                t0 = time.monotonic()
                n_a = constituent_pe_service.backfill_index_pe(session, idx)
                session.commit()
                log.info("backfill.aggregate_done", code=code, rows=n_a,
                         seconds=round(time.monotonic() - t0, 1))

            # 验收：最新一天聚合 PE
            pe, d, meta = constituent_pe_service.latest_aggregate_pe(session, idx)
            log.info("backfill.summary", code=code, date=d,
                     pe=float(pe) if pe else None, **meta)


if __name__ == "__main__":
    main()
