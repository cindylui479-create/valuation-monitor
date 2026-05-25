from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, select

from app.config import get_settings
from app.scheduler.jobs import _run_pipeline, register_jobs
from app.utils.logging import get_logger

log = get_logger("scheduler")

_scheduler: BackgroundScheduler | None = None

# 启动时检查的"漏跑阈值"：上次入库距今超过 30 小时即认为漏跑
CATCH_UP_THRESHOLD_HOURS = 30


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    settings = get_settings()
    sched = BackgroundScheduler(timezone=settings.tz)
    register_jobs(sched)
    sched.start()
    _scheduler = sched
    log.info("scheduler.started")
    # 异步触发漏跑补跑（不阻塞 uvicorn 启动）
    threading.Thread(target=_catch_up_missed_runs, daemon=True,
                     name="scheduler-catch-up").start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler.stopped")


def _enabled_markets() -> list[str]:
    s = get_settings()
    out = []
    if s.schedule_a_enabled: out.append("A")
    if s.schedule_hk_enabled: out.append("HK")
    if s.schedule_us_enabled: out.append("US")
    return out


def _last_quote_created_at(market_code: str) -> str | None:
    """返回该市场所有指数的 max(index_quote.created_at)（ISO 字符串）。"""
    # 延迟导入避免循环依赖
    from app.db import SessionLocal
    from app.models import IndexMeta, IndexQuote, Market
    with SessionLocal() as session:
        m = session.scalar(select(Market).where(Market.code == market_code))
        if m is None:
            return None
        return session.scalar(
            select(func.max(IndexQuote.created_at))
            .join(IndexMeta, IndexMeta.id == IndexQuote.index_id)
            .where(IndexMeta.market_id == m.id)
        )


def _should_catch_up(last_iso: str | None, now: datetime, threshold_hours: int) -> bool:
    """判断该市场是否需要立即补跑：从未入库 / 距上次超过阈值。"""
    if last_iso is None:
        return True
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (now - last) > timedelta(hours=threshold_hours)


def _catch_up_missed_runs() -> None:
    """对每个启用市场检查最近一次入库时间，若 > 阈值则立即触发一次补跑。

    通过 _run_pipeline 同步调用（在 daemon thread 中）；不阻塞主进程。
    """
    now = datetime.now(timezone.utc)
    for m in _enabled_markets():
        last = _last_quote_created_at(m)
        if not _should_catch_up(last, now, CATCH_UP_THRESHOLD_HOURS):
            log.info("scheduler.catch_up.skipped", market=m, last_quote=last)
            continue
        log.warning("scheduler.catch_up.triggered", market=m, last_quote=last,
                    threshold_hours=CATCH_UP_THRESHOLD_HOURS)
        try:
            _run_pipeline(m)
        except Exception as e:
            log.error("scheduler.catch_up.failed", market=m, error=str(e)[:200])
