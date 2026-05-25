"""SRS v1.1.0 方案 A：Tushare 拉取成分股权重 + 个股日频估值。

封装在 service 层（而不是 adapter）因为：
- 多次调用、限频处理、批量写库
- 单纯调 Tushare 的部分逻辑薄，封装成自包含的 fetcher

Tushare 2000 积分接口频率限制：200/min。本模块自动 sleep 节流。
"""
from __future__ import annotations

import time
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import get_settings
from app.repositories import constituent_repo
from app.utils.exceptions import FetchFailure
from app.utils.logging import get_logger

log = get_logger("constituent_fetcher")

# Tushare 节流：2000 积分用户 200次/分；保守用 6/秒 + 0.2 秒间隔
_MIN_INTERVAL_S = 0.35


def _get_pro():
    token = (get_settings().tushare_token or "").strip()
    if not token:
        raise FetchFailure("TUSHARE_TOKEN not set")
    try:
        import tushare as ts
    except ImportError as e:
        raise FetchFailure(f"tushare not installed: {e}") from e
    ts.set_token(token)
    return ts.pro_api(timeout=180)


def _normalize_ts_code(code: str) -> str:
    """000300.SH/H30269.CSI 已 OK；裸 6 位数字转 .SH/.SZ。"""
    return code.strip()


def fetch_index_weights(
    session: Session, index_id: int, ts_code: str,
    *, start: date, end: date,
) -> int:
    """从 Tushare 拉指数月度权重，写入 IndexConstituent。

    返回新插入/变更的行数。
    """
    pro = _get_pro()
    start_s = start.strftime("%Y%m%d")
    end_s = end.strftime("%Y%m%d")
    try:
        df = pro.index_weight(index_code=ts_code, start_date=start_s, end_date=end_s)
    except Exception as e:
        raise FetchFailure(f"index_weight {ts_code}: {e}") from e
    if df is None or df.empty:
        log.warning("constituent.weights_empty", code=ts_code)
        return 0

    df = df.sort_values("trade_date")
    n = 0
    for _, r in df.iterrows():
        d_raw = str(r["trade_date"])
        date_iso = f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}"
        if constituent_repo.upsert_constituent(
            session, index_id, date_iso,
            stock_code=str(r["con_code"]),
            weight=Decimal(str(r["weight"])),
        ):
            n += 1
    return n


def fetch_constituent_quotes(
    session: Session, stock_codes: list[str],
    *, start: date, end: date,
    skip_existing: bool = True,
) -> tuple[int, int]:
    """批量拉成分股日频 daily_basic，写入 IndexConstituentQuote。

    skip_existing=True 时，已有数据的 stock_code 跳过（用于幂等首次 backfill）。

    返回 (n_stocks_processed, n_rows_upserted)。
    """
    pro = _get_pro()
    start_s = start.strftime("%Y%m%d")
    end_s = end.strftime("%Y%m%d")

    n_stocks = 0
    n_rows = 0
    last_call_at = 0.0

    for code in stock_codes:
        if skip_existing and constituent_repo.has_data(session, code):
            log.debug("constituent.skip_existing", code=code)
            continue

        # 节流
        elapsed = time.monotonic() - last_call_at
        if elapsed < _MIN_INTERVAL_S:
            time.sleep(_MIN_INTERVAL_S - elapsed)
        last_call_at = time.monotonic()

        try:
            df = pro.daily_basic(
                ts_code=code, start_date=start_s, end_date=end_s,
                fields="trade_date,total_mv,pe_ttm,pb",
            )
        except Exception as e:
            log.warning("constituent.fetch_fail", code=code, error=str(e)[:120])
            continue
        if df is None or df.empty:
            log.debug("constituent.empty", code=code)
            n_stocks += 1
            continue

        df = df.sort_values("trade_date")
        for _, r in df.iterrows():
            d_raw = str(r["trade_date"])
            date_iso = f"{d_raw[:4]}-{d_raw[4:6]}-{d_raw[6:8]}"
            from app.utils.decimal_utils import to_decimal
            if constituent_repo.upsert_quote(
                session, code, date_iso,
                total_mv=to_decimal(r.get("total_mv")),
                pe_ttm=to_decimal(r.get("pe_ttm")),
                pb=to_decimal(r.get("pb")),
                source="tushare",
            ):
                n_rows += 1
        n_stocks += 1
        if n_stocks % 20 == 0:
            session.commit()
            log.info("constituent.progress", n_stocks=n_stocks, n_rows=n_rows)

    session.commit()
    return n_stocks, n_rows
