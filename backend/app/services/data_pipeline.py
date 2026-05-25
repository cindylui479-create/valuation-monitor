"""每日批处理编排：拉取 → 入库 → 重算分位。

M1：仅 A 股；信号 / 定投生成在 M4 接入。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_registry
from app.models import IndexMeta, IndexQuote
from app.repositories import audit_repo, index_repo, quote_repo
from app.services import valuation_service
from app.utils.exceptions import DataSourceError, FetchFailure
from app.utils.logging import get_logger
from app.utils.time_utils import now_iso, today_iso

log = get_logger("pipeline")

# D2：每次拉取覆盖最近 30 个交易日
LOOKBACK_DAYS = 30


@dataclass
class PipelineResult:
    market: str
    started_at: str
    finished_at: str
    success: bool
    indices_processed: int
    rows_upserted: int
    rows_changed: int
    errors: list[str]


def run_for_market(session: Session, market: str, target_date: date | None = None) -> PipelineResult:
    started = now_iso()
    target = target_date or date.today()
    start = target - timedelta(days=LOOKBACK_DAYS)
    log.info("pipeline.start", market=market, start=start.isoformat(), end=target.isoformat())

    indices = index_repo.list_indices(session, market_code=market)
    if not indices:
        log.warning("pipeline.no_indices", market=market)
        return PipelineResult(market, started, now_iso(), True, 0, 0, 0, [])

    registry = get_registry()
    if not registry.fallbacks(market):
        msg = f"no adapter registered for market {market}"
        log.error("pipeline.no_adapter", market=market)
        return PipelineResult(market, started, now_iso(), False, 0, 0, 0, [msg])

    rows_upserted = 0
    rows_changed = 0
    errors: list[str] = []

    for idx in indices:
        try:
            adapters_for_idx = registry.fallbacks_for_index(market, idx.code)
            n_up, n_ch = _ingest_one(session, idx, start, target, adapters_for_idx)
            rows_upserted += n_up
            rows_changed += n_ch
        except DataSourceError as e:
            errors.append(f"{idx.code}: {e}")
            log.error("pipeline.index_failed", code=idx.code, error=str(e))

    session.commit()

    # SRS v1.1.0 方案 A：A 市场 3 只指数走成分股聚合 PE
    if market == "A":
        try:
            n_set = _augment_constituent_pe(session, start, target)
            session.commit()
            log.info("pipeline.constituent_pe_augmented", market=market, set=n_set)
        except Exception as e:
            errors.append(f"constituent_pe {market}: {e}")
            log.error("pipeline.constituent_pe_failed", market=market, error=str(e)[:200])

    # SRS R10：双口径 — Tushare 覆盖的 A 股指数额外拉一次 CSI 数据填 pe_ttm_csi/pb_csi
    if market == "A":
        try:
            n_csi = _augment_csi(session, indices, start, target)
            session.commit()
            log.info("pipeline.csi_augmented", market=market, count=n_csi)
        except Exception as e:
            errors.append(f"csi augment: {e}")
            log.error("pipeline.csi_augment_failed", error=str(e)[:200])

    # SRS v1.1.0 方案 B：US 市场每日拉一次 multpl S&P 500 PE，forward-fill 到 SPY 当月 quotes
    if market == "US":
        try:
            n_set = _augment_multpl_spy(session)
            session.commit()
            log.info("pipeline.multpl_augmented", market=market, set=n_set)
        except Exception as e:
            errors.append(f"multpl {market}: {e}")
            log.error("pipeline.multpl_failed", market=market, error=str(e)[:200])

    # 重算最近 30 个交易日的派生分位（两个口径都算）
    dates_to_recompute = _recent_dates(target, LOOKBACK_DAYS)
    for idx in indices:
        try:
            valuation_service.recompute_for_index(session, idx, dates_to_recompute)
        except Exception as e:
            errors.append(f"valuation {idx.code}: {e}")
            log.error("pipeline.valuation_failed", code=idx.code, error=str(e))
    session.commit()

    # SRS R12 M6-A：A 市场调度内顺带跑个股日常增量
    if market == "A":
        try:
            from app.services import stock_pipeline

            results = stock_pipeline.daily_increment(session, lookback_days=LOOKBACK_DAYS)
            log.info("pipeline.stocks_done", market=market,
                     count=len(results), failed=sum(1 for r in results if r.error))
        except Exception as e:
            errors.append(f"stocks {market}: {e}")
            log.error("pipeline.stocks_failed", market=market, error=str(e))

        # SRS R12 M7-B：A 市场调度内拉主动基金 NAV
        try:
            from app.services import fund_pipeline

            fund_results = fund_pipeline.daily_increment(session, lookback_days=10)
            log.info("pipeline.funds_done", market=market,
                     count=len(fund_results), failed=sum(1 for r in fund_results if r.error))
        except Exception as e:
            errors.append(f"funds {market}: {e}")
            log.error("pipeline.funds_failed", market=market, error=str(e))

    # SRS R11：数据异常检测（最近 10 天 lookback，不改 temperature/percentile 数字）
    try:
        from app.services import data_quality

        dq_new = 0
        dq_refresh = 0
        for idx in indices:
            try:
                n, r = data_quality.detect_and_persist(session, idx, lookback_days=10)
                dq_new += n
                dq_refresh += r
            except Exception as e:
                log.warning("pipeline.dq_skip", code=idx.code, error=str(e)[:120])
        session.commit()
        log.info("pipeline.data_quality", market=market, new=dq_new, refreshed=dq_refresh)
    except Exception as e:
        errors.append(f"data_quality {market}: {e}")
        log.error("pipeline.dq_failed", market=market, error=str(e))

    # M4 + R10：双口径都跑一次（lg + csi），signal 表按 source 区分
    try:
        from app.services import signal_engine

        n_lg = signal_engine.generate_signals_for(
            session, market_code=market, date_=target.isoformat(), source="lg"
        )
        n_csi = signal_engine.generate_signals_for(
            session, market_code=market, date_=target.isoformat(), source="csi"
        )
        session.commit()
        log.info("pipeline.signals_generated", market=market, lg=n_lg, csi=n_csi)
    except Exception as e:
        errors.append(f"signal {market}: {e}")
        log.error("pipeline.signal_failed", market=market, error=str(e))

    # M4：刷新定投提醒
    try:
        from app.services import dca_planner

        n_exec = dca_planner.refresh_executions_for_market(session, market_code=market, today=target)
        session.commit()
        log.info("pipeline.dca_refreshed", market=market, count=n_exec)
    except Exception as e:
        errors.append(f"dca {market}: {e}")
        log.error("pipeline.dca_failed", market=market, error=str(e))

    finished = now_iso()
    success = not errors
    log.info(
        "pipeline.done",
        market=market,
        success=success,
        rows_upserted=rows_upserted,
        rows_changed=rows_changed,
        errors=len(errors),
    )
    return PipelineResult(
        market=market,
        started_at=started,
        finished_at=finished,
        success=success,
        indices_processed=len(indices),
        rows_upserted=rows_upserted,
        rows_changed=rows_changed,
        errors=errors,
    )


def _ingest_one(
    session: Session,
    idx: IndexMeta,
    start: date,
    end: date,
    adapters,
) -> tuple[int, int]:
    """多源回退拉取 + upsert + 审计日志。返回 (upserted_count, changed_count)。"""
    last_err: Exception | None = None
    for adp in adapters:
        try:
            rows = list(adp.fetch_quotes([idx.code], start, end))
            return _persist_rows(session, idx, rows, adp.name)
        except FetchFailure as e:
            last_err = e
            log.warning("pipeline.adapter_fallback", code=idx.code, adapter=adp.name, error=str(e))
            continue
    raise DataSourceError(f"all adapters failed for {idx.code}: {last_err}")


def _persist_rows(
    session: Session, idx: IndexMeta, rows, source: str
) -> tuple[int, int]:
    n_up = 0
    n_ch = 0
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
            source=source,
            created_at=today_iso(),
        )
        changed, diffs = quote_repo.upsert_quote(session, q, source=source)
        if changed:
            n_ch += 1
            record_key = f"index_quote:{idx.code}:{r.date}"
            for field, old_v, new_v in diffs:
                audit_repo.log_change(
                    session,
                    table="index_quote",
                    record_key=record_key,
                    field=field,
                    old_value=old_v,
                    new_value=new_v,
                    source=source,
                )
        n_up += 1
    return n_up, n_ch


def _recent_dates(end: date, days: int) -> list[str]:
    return [(end - timedelta(days=i)).isoformat() for i in range(days)]


# SRS R10：Tushare 覆盖的指数（pe_ttm_csi/pb_csi 可独立填充）
TUSHARE_CSI_COVERED = {
    "000300.SH", "000905.SH", "000016.SH",
    "000001.SH", "399001.SZ", "399006.SZ",
}


CONSTITUENT_PE_INDICES = ("000932.SH", "H30269.CSI", "000688.SH")


def _augment_constituent_pe(session, start: date, end: date) -> int:
    """SRS v1.1.0 方案 A：每日批处理 — 对 3 只指数同步成分股权重 + quotes，
    并对最近 30 天重算成分股聚合 PE → 写 index_quote.pe_ttm。

    Tushare 调用密集；只在 A 调度内跑一次。返回更新的 index_quote 行数。
    """
    from app.repositories import constituent_repo, index_repo
    from app.services import constituent_fetcher, constituent_pe_service

    n_total = 0
    for code in CONSTITUENT_PE_INDICES:
        idx = index_repo.get_by_code(session, code)
        if idx is None:
            continue
        try:
            # 1) 拉最近 60 天的月度权重（保证当月调样能跟上）
            constituent_fetcher.fetch_index_weights(
                session, idx.id, code,
                start=end - timedelta(days=60), end=end,
            )
            session.commit()

            # 2) 拉成分股近 30 天 daily_basic（增量；已有不跳过 — pe 每日变）
            stock_codes = constituent_repo.list_distinct_stock_codes(session, idx.id)
            constituent_fetcher.fetch_constituent_quotes(
                session, stock_codes,
                start=end - timedelta(days=30), end=end,
                skip_existing=False,
            )
            session.commit()

            # 3) 重算最近 30 天聚合 PE
            n = constituent_pe_service.backfill_index_pe(
                session, idx,
                start=(end - timedelta(days=30)).isoformat(),
                end=end.isoformat(),
            )
            n_total += n
            session.commit()
        except Exception as e:
            log.warning("constituent_pe.daily_fail", code=code, error=str(e)[:200])
    return n_total


def _augment_multpl_spy(session) -> int:
    """SRS v1.1.0 方案 B：拉 multpl S&P 500 PE-TTM 月度数据，
    forward-fill 到 SPY 的近 60 天 index_quote.pe_ttm（覆盖月初 + 当月所有交易日）。

    幂等：值未变时不更新；返回实际更新的行数。
    """
    import bisect
    from decimal import Decimal

    from app.adapters.multpl_adapter import MultplAdapter
    from app.models import IndexMeta, IndexQuote

    idx = session.scalar(select(IndexMeta).where(IndexMeta.code == "SPY"))
    if idx is None:
        return 0

    adapter = MultplAdapter()
    try:
        points = list(adapter.fetch_history("s-p-500-pe-ratio"))
    except Exception as e:
        log.warning("multpl.fetch_failed", error=str(e)[:200])
        return 0
    if not points:
        return 0

    monthly = sorted([(date.fromisoformat(p.date), p.value) for p in points])
    m_dates = [d for d, _ in monthly]
    m_vals = [v for _, v in monthly]

    def lookup(d_: date) -> Decimal | None:
        i = bisect.bisect_right(m_dates, d_) - 1
        return m_vals[i] if i >= 0 else None

    # 只更近 60 天（每日增量场景；首次 backfill 走 scripts/backfill_multpl_spy.py）
    end = date.today()
    start = end - timedelta(days=60)
    n_set = 0
    quotes = list(session.scalars(
        select(IndexQuote)
        .where(IndexQuote.index_id == idx.id)
        .where(IndexQuote.date >= start.isoformat())
        .where(IndexQuote.date <= end.isoformat())
    ))
    for q in quotes:
        pe = lookup(date.fromisoformat(q.date))
        if pe is None:
            continue
        if q.pe_ttm is not None and abs(Decimal(str(q.pe_ttm)) - pe) < Decimal("0.001"):
            continue
        q.pe_ttm = pe
        if not q.source:
            q.source = "multpl"
        elif "multpl" not in q.source:
            q.source = f"{q.source}+multpl"
        n_set += 1
    return n_set


def _augment_csi(session, indices, start: date, end: date) -> int:
    """对 Tushare 覆盖的指数额外拉一次 CSI 数据，填到 pe_ttm_csi / pb_csi 两列。

    返回更新的行数。失败/无 token 时静默跳过（不阻塞主流程）。
    """
    targets = [i for i in indices if i.code in TUSHARE_CSI_COVERED]
    if not targets:
        return 0
    try:
        from app.adapters.tushare_adapter import TushareAdapter
        ts = TushareAdapter()
    except Exception:
        return 0

    n = 0
    for idx in targets:
        try:
            rows = list(ts.fetch_quotes([idx.code], start, end))
        except Exception as e:
            log.warning("pipeline.csi_augment_skip", code=idx.code, error=str(e)[:120])
            continue
        for r in rows:
            updated = quote_repo.update_csi_values(
                session, idx.id, r.date, r.pe_ttm, r.pb
            )
            if updated:
                n += 1
    return n
