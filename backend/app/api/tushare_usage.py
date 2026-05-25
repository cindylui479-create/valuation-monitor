"""SRS v1.3.0 E：Tushare 配额监控 API。

GET /api/v1/tushare-usage
返回今日 / 本月 / 近 30 天的 Tushare 调用统计 + 失败率。
按接口分组明细。
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import TushareCallLog

router = APIRouter()


class InterfaceStat(BaseModel):
    interface: str
    n_calls: int
    n_failures: int
    last_error_message: str | None


class DailyStat(BaseModel):
    date: str
    n_calls: int
    n_failures: int


class TushareUsageResponse(BaseModel):
    today: dict             # {date, total_calls, total_failures, by_interface}
    month: dict             # 本月汇总
    last_30_days: list[DailyStat]
    by_interface_30d: list[InterfaceStat]


def _sum_by_interface(rows: list[TushareCallLog]) -> list[InterfaceStat]:
    agg: dict[str, dict] = {}
    for r in rows:
        a = agg.setdefault(r.interface, {"n_calls": 0, "n_failures": 0, "last_error": None})
        a["n_calls"] += r.n_calls
        a["n_failures"] += r.n_failures
        if r.last_error_message and (a["last_error"] is None):
            a["last_error"] = r.last_error_message
    return [
        InterfaceStat(
            interface=iface, n_calls=v["n_calls"], n_failures=v["n_failures"],
            last_error_message=v["last_error"],
        )
        for iface, v in sorted(agg.items(), key=lambda kv: -kv[1]["n_calls"])
    ]


@router.get("/tushare-usage", response_model=TushareUsageResponse)
def tushare_usage(session: Session = Depends(db_session)) -> TushareUsageResponse:
    today = date.today()
    today_s = today.isoformat()
    month_start = today.replace(day=1).isoformat()
    cutoff_30d = (today - timedelta(days=30)).isoformat()

    # 今日
    today_rows = list(session.scalars(
        select(TushareCallLog).where(TushareCallLog.call_date == today_s)
    ))
    today_calls = sum(r.n_calls for r in today_rows)
    today_failures = sum(r.n_failures for r in today_rows)

    # 本月
    month_rows = list(session.scalars(
        select(TushareCallLog).where(TushareCallLog.call_date >= month_start)
    ))
    month_calls = sum(r.n_calls for r in month_rows)
    month_failures = sum(r.n_failures for r in month_rows)

    # 近 30 天逐日
    daily_q = (
        select(
            TushareCallLog.call_date,
            func.sum(TushareCallLog.n_calls).label("calls"),
            func.sum(TushareCallLog.n_failures).label("failures"),
        )
        .where(TushareCallLog.call_date >= cutoff_30d)
        .group_by(TushareCallLog.call_date)
        .order_by(TushareCallLog.call_date.asc())
    )
    daily = [
        DailyStat(date=r[0], n_calls=int(r[1] or 0), n_failures=int(r[2] or 0))
        for r in session.execute(daily_q).all()
    ]

    # 近 30 天按接口
    iface_rows = list(session.scalars(
        select(TushareCallLog).where(TushareCallLog.call_date >= cutoff_30d)
    ))
    iface_30d = _sum_by_interface(iface_rows)

    return TushareUsageResponse(
        today={
            "date": today_s,
            "total_calls": today_calls,
            "total_failures": today_failures,
            "by_interface": [s.model_dump() for s in _sum_by_interface(today_rows)],
        },
        month={
            "month_start": month_start,
            "total_calls": month_calls,
            "total_failures": month_failures,
        },
        last_30_days=daily,
        by_interface_30d=iface_30d,
    )
