"""运行历史聚合（M5 后置增强）。

按 created_at::date + market 聚合 4 张事件表，给出每天每市场一行汇总。
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.deps import db_session

router = APIRouter()


class PipelineRunDay(BaseModel):
    date: str
    market: str
    quotes_upserted: int
    audits_logged: int
    signals_generated: int
    dca_executions_generated: int
    first_event_at: str | None
    last_event_at: str | None


class PipelineRunsResponse(BaseModel):
    items: list[PipelineRunDay]
    days: int


@router.get("/pipeline-runs", response_model=PipelineRunsResponse)
def list_pipeline_runs(
    days: int = Query(default=30, ge=1, le=365),
    session: Session = Depends(db_session),
) -> PipelineRunsResponse:
    """聚合 index_quote / data_audit / signal / dca_execution 四张表
    的 *created_at / audit_time / generated_at* 字段，按 (日期, 市场) 分组。

    "日期" = ISO timestamp 的前 10 字符；"市场" 来自 index_meta.market 关联。
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    # 各事件表分别按 (run_date, market) 聚合，再 FULL OUTER JOIN 起来。
    # SQLite 不支持 FULL OUTER JOIN，用 UNION ALL + 外层 GROUP BY 模拟。
    sql = text("""
        WITH quotes AS (
            SELECT substr(q.created_at, 1, 10) AS run_date,
                   m.code AS market,
                   COUNT(*) AS n,
                   MIN(q.created_at) AS first_at,
                   MAX(q.created_at) AS last_at
            FROM index_quote q
            JOIN index_meta i ON i.id = q.index_id
            JOIN market m ON m.id = i.market_id
            WHERE substr(q.created_at, 1, 10) >= :cutoff
            GROUP BY run_date, market
        ),
        audits AS (
            SELECT substr(a.audit_time, 1, 10) AS run_date,
                   m.code AS market,
                   COUNT(*) AS n,
                   MIN(a.audit_time) AS first_at,
                   MAX(a.audit_time) AS last_at
            FROM data_audit a
            JOIN index_meta i ON i.code = substr(a.record_key, length('index_quote:') + 1,
                                                  instr(substr(a.record_key, length('index_quote:') + 1), ':') - 1)
            JOIN market m ON m.id = i.market_id
            WHERE substr(a.audit_time, 1, 10) >= :cutoff
            GROUP BY run_date, market
        ),
        signals AS (
            SELECT substr(s.generated_at, 1, 10) AS run_date,
                   m.code AS market,
                   COUNT(*) AS n,
                   MIN(s.generated_at) AS first_at,
                   MAX(s.generated_at) AS last_at
            FROM signal s
            JOIN index_meta i ON i.id = s.index_id
            JOIN market m ON m.id = i.market_id
            WHERE substr(s.generated_at, 1, 10) >= :cutoff
            GROUP BY run_date, market
        ),
        dcas AS (
            SELECT substr(e.generated_at, 1, 10) AS run_date,
                   m.code AS market,
                   COUNT(*) AS n,
                   MIN(e.generated_at) AS first_at,
                   MAX(e.generated_at) AS last_at
            FROM dca_execution e
            JOIN dca_plan p ON p.id = e.plan_id
            JOIN index_meta i ON i.id = p.index_id
            JOIN market m ON m.id = i.market_id
            WHERE substr(e.generated_at, 1, 10) >= :cutoff
            GROUP BY run_date, market
        ),
        combined AS (
            SELECT run_date, market, n AS quotes_upserted, 0 AS audits_logged,
                   0 AS signals_generated, 0 AS dca_executions_generated,
                   first_at, last_at FROM quotes
            UNION ALL
            SELECT run_date, market, 0, n, 0, 0, first_at, last_at FROM audits
            UNION ALL
            SELECT run_date, market, 0, 0, n, 0, first_at, last_at FROM signals
            UNION ALL
            SELECT run_date, market, 0, 0, 0, n, first_at, last_at FROM dcas
        )
        SELECT run_date, market,
               SUM(quotes_upserted) AS quotes_upserted,
               SUM(audits_logged)   AS audits_logged,
               SUM(signals_generated) AS signals_generated,
               SUM(dca_executions_generated) AS dca_executions_generated,
               MIN(first_at) AS first_event_at,
               MAX(last_at)  AS last_event_at
        FROM combined
        GROUP BY run_date, market
        ORDER BY run_date DESC, market
    """)

    rows = session.execute(sql, {"cutoff": cutoff}).all()
    items = [
        PipelineRunDay(
            date=r.run_date,
            market=r.market,
            quotes_upserted=int(r.quotes_upserted or 0),
            audits_logged=int(r.audits_logged or 0),
            signals_generated=int(r.signals_generated or 0),
            dca_executions_generated=int(r.dca_executions_generated or 0),
            first_event_at=r.first_event_at,
            last_event_at=r.last_event_at,
        )
        for r in rows
    ]
    return PipelineRunsResponse(items=items, days=days)
