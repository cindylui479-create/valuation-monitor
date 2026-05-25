"""SRS v1.1.0 方案 B：用 multpl.com S&P 500 PE-TTM 月度数据
补全 SPY 在 index_quote 表中的 pe_ttm 字段。

策略：multpl 是月度数据点（如 "Jan 1, 2026 → 29.60"）；
SPY index_quote 是日频。每个 multpl 数据点应用到该月起到下个 multpl 点之间的
所有 SPY 交易日（即 forward-fill / 月度 → 日频展开）。

用法：
    python -m scripts.backfill_multpl_spy [--dry-run]
"""
from __future__ import annotations

import argparse
import bisect
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select

from app.adapters.multpl_adapter import MultplAdapter
from app.db import SessionLocal
from app.models import IndexMeta, IndexQuote, Market
from app.utils.logging import get_logger, setup_logging

log = get_logger("backfill_multpl")


def _forward_fill(monthly: list[tuple[date, Decimal]]) -> callable:
    """返回函数 f(date) → Decimal | None：取 date 所在月或之前最近的 multpl 值。

    monthly 必须已按 date 升序。
    """
    dates = [d for d, _ in monthly]
    values = [v for _, v in monthly]

    def lookup(d: date) -> Decimal | None:
        # bisect_right：返回插入位置；前一位是 <= d 的最大 multpl 月
        idx = bisect.bisect_right(dates, d) - 1
        if idx < 0:
            return None
        return values[idx]

    return lookup


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只读，不写库")
    parser.add_argument("--code", default="SPY")
    args = parser.parse_args()

    # 1) 拉 multpl 月度 PE
    adapter = MultplAdapter()
    points = list(adapter.fetch_history("s-p-500-pe-ratio"))
    monthly = sorted([(date.fromisoformat(p.date), p.value) for p in points])
    log.info("multpl.parsed",
             rows=len(monthly),
             range=f"{monthly[0][0]} ~ {monthly[-1][0]}")
    lookup = _forward_fill(monthly)

    # 2) 在 DB 中找 SPY 的所有 quote 行
    with SessionLocal() as session:
        idx = session.scalar(select(IndexMeta).where(IndexMeta.code == args.code))
        if idx is None:
            log.error("backfill.index_not_found", code=args.code)
            return

        market = session.scalar(select(Market).where(Market.id == idx.market_id))
        log.info("backfill.start", code=args.code, market=market.code if market else "?")

        quotes = list(session.scalars(
            select(IndexQuote).where(IndexQuote.index_id == idx.id).order_by(IndexQuote.date)
        ))
        log.info("backfill.quotes", code=args.code, n=len(quotes))

        # 3) 对每行 quote.pe_ttm 写 forward-filled 月度值
        n_set = 0
        n_skip = 0
        for q in quotes:
            d = date.fromisoformat(q.date)
            pe = lookup(d)
            if pe is None:
                n_skip += 1
                continue
            # 若 pe_ttm 与新值差异 < 0.001，跳过（幂等）
            if q.pe_ttm is not None and abs(Decimal(str(q.pe_ttm)) - pe) < Decimal("0.001"):
                continue
            if not args.dry_run:
                q.pe_ttm = pe
                # 标识来源；保留 close 仍由 yfinance 拉
                if q.source and "multpl" not in q.source:
                    q.source = f"{q.source}+multpl"
                elif not q.source:
                    q.source = "multpl"
            n_set += 1

        if not args.dry_run:
            session.commit()
        log.info("backfill.done",
                 code=args.code, set=n_set, skipped_pre1871=n_skip,
                 dry_run=args.dry_run)


if __name__ == "__main__":
    main()
