"""APScheduler 三地 cron 任务定义。

调度时刻表见 SRS D3：
- A 股：UTC+8 16:30
- 港股：UTC+8 17:30
- 美股：UTC+8 次日 07:00

SRS 附录 B R9（鲁棒性增强）：
- misfire_grace_time = 6h：休眠/进程暂停后醒来，6 小时内仍可补跑
- coalesce = True：错过多次（如机器睡了 2 天）合并为一次执行
- 服务启动时的"漏跑补跑"在 scheduler.runner._catch_up_missed_runs 处理（>30h 未跑则补）
"""
from __future__ import annotations

import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.db import SessionLocal
from app.services import data_pipeline
from app.services.health_service import state
from app.utils.logging import get_logger
from app.utils.time_utils import now_iso

log = get_logger("scheduler")


def _run_pipeline(market: str) -> None:
    start = time.monotonic()
    log.info("scheduler.job.start", market=market)
    with SessionLocal() as session:
        result = data_pipeline.run_for_market(session, market=market)
    duration = time.monotonic() - start
    status = "SUCCESS" if result.success else ("PARTIAL" if result.rows_upserted > 0 else "FAILED")
    state().record_pipeline(
        market=market,
        last_run_at=now_iso(),
        status=status,
        duration_seconds=duration,
        errors=result.errors,
    )
    log.info("scheduler.job.done", market=market, status=status, duration=duration)


MISFIRE_GRACE_SECONDS = 6 * 3600   # 6 小时
COALESCE = True                      # 多次错过合并为一次


def register_jobs(scheduler: BackgroundScheduler) -> None:
    settings = get_settings()
    tz = settings.tz

    common = dict(
        replace_existing=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
        coalesce=COALESCE,
    )

    if settings.schedule_a_enabled:
        scheduler.add_job(
            _run_pipeline,
            args=["A"],
            trigger=CronTrigger(hour=16, minute=30, timezone=tz),
            id="pipeline_a",
            **common,
        )
        log.info("scheduler.registered", job="pipeline_a", schedule="16:30 daily",
                 misfire_grace_h=MISFIRE_GRACE_SECONDS / 3600)

    if settings.schedule_hk_enabled:
        scheduler.add_job(
            _run_pipeline,
            args=["HK"],
            trigger=CronTrigger(hour=17, minute=30, timezone=tz),
            id="pipeline_hk",
            **common,
        )
        log.info("scheduler.registered", job="pipeline_hk", schedule="17:30 daily")

    if settings.schedule_us_enabled:
        scheduler.add_job(
            _run_pipeline,
            args=["US"],
            trigger=CronTrigger(hour=7, minute=0, timezone=tz),
            id="pipeline_us",
            **common,
        )
        log.info("scheduler.registered", job="pipeline_us", schedule="07:00 daily")
