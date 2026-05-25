"""SRS v1.1.0 方案 A §11.2.x：成分股加权聚合 PE-TTM（整体法）。

公式（CSI 官方整体法）：
    PE_index(t) = Σ market_cap_i(t)  /  Σ net_profit_ttm_i(t)
                = Σ mv_i / Σ (mv_i / pe_i)

剔除规则：
- pe_i 为 None 或 ≤ 0（亏损股）→ 该成分股不计入分母（但 mv 仍计入分子吗？
  CSI 官方做法是**整体含亏损**，但很多场景剔除亏损；这里我们**剔除亏损成分**，
  即 mv 和分母都不算 — 与"扣除亏损股的整体法"一致，温度比含亏损更稳定）

权重应用：
- IndexConstituent 是月度报告；对每个交易日 d 取最近一次月度成分股 + 权重
- 当日的 mv / pe 从 IndexConstituentQuote 拉
- 权重在公式中**不直接出现**（整体法直接用绝对市值聚合），但
  index_weight 提供的成分股清单作为筛选条件

未来扩展：
- weight × pe 加权平均 （简化版）
- 含亏损股的整体法（CSI 官方）
"""
from __future__ import annotations

from datetime import date as _date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import IndexMeta, IndexQuote
from app.repositories import constituent_repo, quote_repo
from app.utils.logging import get_logger
from app.utils.time_utils import now_iso

log = get_logger("constituent_pe")


def aggregate_pe_for_date(
    session: Session, index: IndexMeta, d: str,
) -> tuple[Decimal | None, dict]:
    """对单日单指数做整体法聚合 PE-TTM。

    返回 (pe, meta)，meta 含 n_eligible, n_total, dropped_codes 等诊断信息。
    """
    constituents = constituent_repo.get_weights_on(session, index.id, d)
    if not constituents:
        return None, {"reason": "no_constituents", "n_total": 0}

    stock_codes = [c.stock_code for c in constituents]
    quotes = constituent_repo.get_quotes_batch(session, stock_codes, d)

    sum_mv = Decimal(0)
    sum_profit = Decimal(0)
    dropped_no_quote = []
    dropped_negative_pe = []
    n_eligible = 0

    for c in constituents:
        q = quotes.get(c.stock_code)
        if q is None or q.total_mv is None or q.pe_ttm is None:
            dropped_no_quote.append(c.stock_code)
            continue
        if q.pe_ttm <= 0:
            dropped_negative_pe.append(c.stock_code)
            continue
        # net_profit_ttm = mv / pe_ttm
        profit = q.total_mv / q.pe_ttm
        sum_mv += q.total_mv
        sum_profit += profit
        n_eligible += 1

    if sum_profit == 0 or n_eligible == 0:
        return None, {
            "reason": "no_eligible_quotes",
            "n_total": len(constituents),
            "n_eligible": n_eligible,
            "n_dropped_no_quote": len(dropped_no_quote),
            "n_dropped_negative_pe": len(dropped_negative_pe),
            "dropped_no_quote": dropped_no_quote[:10],
            "dropped_negative_pe": dropped_negative_pe[:10],
        }
    pe = sum_mv / sum_profit
    return pe, {
        "n_eligible": n_eligible,
        "n_total": len(constituents),
        "n_dropped_no_quote": len(dropped_no_quote),
        "n_dropped_negative_pe": len(dropped_negative_pe),
        "sum_mv": float(sum_mv),
        "sum_profit": float(sum_profit),
    }


def backfill_index_pe(
    session: Session, index: IndexMeta, *,
    start: str | None = None, end: str | None = None,
) -> int:
    """对 index_quote 表中已存在的每个交易日重算成分股聚合 PE，
    回填到 index_quote.pe_ttm。

    返回更新的行数。
    """
    from sqlalchemy import select
    stmt = select(IndexQuote).where(IndexQuote.index_id == index.id)
    if start:
        stmt = stmt.where(IndexQuote.date >= start)
    if end:
        stmt = stmt.where(IndexQuote.date <= end)
    quotes = list(session.scalars(stmt.order_by(IndexQuote.date)))

    n_set = 0
    n_skip = 0
    for q in quotes:
        pe, meta = aggregate_pe_for_date(session, index, q.date)
        if pe is None:
            n_skip += 1
            continue
        if q.pe_ttm is not None and abs(q.pe_ttm - pe) < Decimal("0.001"):
            continue
        q.pe_ttm = pe
        if not q.source or "constituent" not in q.source:
            q.source = (q.source + "+constituent") if q.source else "constituent"
        n_set += 1
    log.info("constituent_pe.backfill_done",
             code=index.code, n_set=n_set, n_skip=n_skip)
    return n_set


def latest_aggregate_pe(
    session: Session, index: IndexMeta,
) -> tuple[Decimal | None, str | None, dict]:
    """取 index_quote 表里最新一天的成分股聚合 PE。

    返回 (pe, date, meta)。
    """
    from sqlalchemy import func, select
    last_date = session.scalar(
        select(func.max(IndexQuote.date)).where(IndexQuote.index_id == index.id)
    )
    if last_date is None:
        return None, None, {}
    pe, meta = aggregate_pe_for_date(session, index, last_date)
    return pe, last_date, meta
