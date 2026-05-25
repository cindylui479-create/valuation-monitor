"""SRS v1.3.0 K：seed security_catalog 全市场搜索目录。

数据源：
  STOCK：Tushare stock_basic（全 A 股 ~5400 只）
  FUND：akshare fund_em_fund_name（开放式基金 ~10000+ 只）

用法：
  python -m scripts.seed_catalog              # 全量刷新
  python -m scripts.seed_catalog --skip-fund  # 只刷新 STOCK
"""
from __future__ import annotations

import argparse
import time

from app.adapters.stock_tushare_adapter import _get_pro
from app.db import SessionLocal
from app.models import SecurityCatalog
from app.utils.logging import get_logger, setup_logging
from app.utils.time_utils import now_iso

log = get_logger("seed_catalog")


def seed_stocks(session) -> int:
    pro = _get_pro()
    df = pro.stock_basic(
        exchange="", list_status="L",
        fields="ts_code,name,industry,market",
    )
    if df is None or df.empty:
        log.warning("seed.stocks_empty")
        return 0
    n_set = 0
    from sqlalchemy import select
    for _, r in df.iterrows():
        code = str(r["ts_code"])
        name = str(r["name"])
        industry = str(r["industry"]) if r.get("industry") else None
        existing = session.scalar(
            select(SecurityCatalog).where(
                SecurityCatalog.entity_type == "STOCK",
                SecurityCatalog.code == code,
            )
        )
        if existing is None:
            session.add(SecurityCatalog(
                entity_type="STOCK", code=code, name=name,
                market="A", extra=industry, updated_at=now_iso(),
            ))
            n_set += 1
        elif existing.name != name or existing.extra != industry:
            existing.name = name
            existing.extra = industry
            existing.updated_at = now_iso()
            n_set += 1
    session.commit()
    return n_set


def seed_funds(session) -> int:
    try:
        import akshare as ak
    except ImportError:
        log.warning("seed.akshare_missing")
        return 0
    try:
        df = ak.fund_name_em()
    except Exception as e:
        log.warning("seed.funds_fetch_failed", error=str(e)[:120])
        return 0
    if df is None or df.empty:
        return 0

    # 字段：基金代码 / 拼音缩写 / 基金简称 / 基金类型 / 拼音全称
    n_set = 0
    from sqlalchemy import select
    for _, r in df.iterrows():
        code = str(r.get("基金代码") or "").strip()
        name = str(r.get("基金简称") or "").strip()
        type_raw = str(r.get("基金类型") or "").strip() or None
        if not code or not name:
            continue
        existing = session.scalar(
            select(SecurityCatalog).where(
                SecurityCatalog.entity_type == "FUND",
                SecurityCatalog.code == code,
            )
        )
        if existing is None:
            session.add(SecurityCatalog(
                entity_type="FUND", code=code, name=name,
                market="A", extra=type_raw, updated_at=now_iso(),
            ))
            n_set += 1
        elif existing.name != name or existing.extra != type_raw:
            existing.name = name
            existing.extra = type_raw
            existing.updated_at = now_iso()
            n_set += 1
        if n_set % 2000 == 0 and n_set > 0:
            session.commit()
    session.commit()
    return n_set


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-stock", action="store_true")
    parser.add_argument("--skip-fund", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as session:
        if not args.skip_stock:
            t0 = time.monotonic()
            n = seed_stocks(session)
            log.info("seed.stocks_done", n=n, seconds=round(time.monotonic() - t0, 1))
        if not args.skip_fund:
            t0 = time.monotonic()
            n = seed_funds(session)
            log.info("seed.funds_done", n=n, seconds=round(time.monotonic() - t0, 1))


if __name__ == "__main__":
    main()
