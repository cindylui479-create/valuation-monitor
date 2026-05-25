"""SRS R11：数据异常检测 API。

GET /api/v1/data-quality/summary           汇总每只指数各严重度的异常计数
GET /api/v1/data-quality/{code}            单只指数的全部异常明细
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import db_session
from app.models import Market
from app.repositories import anomaly_repo, index_repo

router = APIRouter()


SEVERITIES = ("HIGH", "MEDIUM", "LOW", "INFO")


class IndexAnomalyCount(BaseModel):
    code: str
    name: str
    market: str
    high: int
    medium: int
    low: int
    info: int
    total: int
    acknowledged: int                # 已核对数（不计入 H/M/L/I）
    latest_anomaly_date: str | None


class DataQualitySummary(BaseModel):
    items: list[IndexAnomalyCount]
    total_anomalies: int


class AnomalyItem(BaseModel):
    id: int
    date: str
    field: str
    source: str
    anomaly_type: str
    severity: str
    value: str | None
    baseline: str | None
    note: str | None
    detected_at: str
    acknowledged_at: str | None
    acknowledged_note: str | None


class AckRequest(BaseModel):
    acknowledged: bool
    note: str | None = None


class AckResponse(BaseModel):
    id: int
    acknowledged_at: str | None
    acknowledged_note: str | None


class IndexAnomalyDetail(BaseModel):
    code: str
    name: str
    market: str
    counts: dict[str, int]
    anomalies: list[AnomalyItem]


def _market_code_map(session: Session) -> dict[int, str]:
    return {m.id: m.code for m in session.query(Market).all()}


@router.get("/data-quality/summary", response_model=DataQualitySummary)
def summary(
    include_acknowledged: bool = Query(default=False),
    session: Session = Depends(db_session),
) -> DataQualitySummary:
    """include_acknowledged=False（默认）：H/M/L/I 计数仅含未核对的异常，
    acknowledged 列单独显示已核对数。"""
    counts = anomaly_repo.counts_by_index_severity(
        session, include_acknowledged=include_acknowledged
    )
    ack_counts = anomaly_repo.counts_acknowledged_by_index(session)
    latest = anomaly_repo.latest_anomaly_date_by_index(session)
    market_codes = _market_code_map(session)

    items: list[IndexAnomalyCount] = []
    total = 0
    for idx in index_repo.list_indices(session):
        per = counts.get(idx.id, {})
        n_h = per.get("HIGH", 0)
        n_m = per.get("MEDIUM", 0)
        n_l = per.get("LOW", 0)
        n_i = per.get("INFO", 0)
        sub = n_h + n_m + n_l + n_i
        total += sub
        market_code = market_codes.get(idx.market_id, "?")
        items.append(IndexAnomalyCount(
            code=idx.code, name=idx.name, market=market_code,
            high=n_h, medium=n_m, low=n_l, info=n_i, total=sub,
            acknowledged=ack_counts.get(idx.id, 0),
            latest_anomaly_date=latest.get(idx.id),
        ))
    # 按"未核对的严重度"降序排（已核对完的指数沉到底部）
    items.sort(key=lambda i: (-i.high, -i.medium, -i.total, i.code))
    return DataQualitySummary(items=items, total_anomalies=total)


@router.get("/data-quality/{code}", response_model=IndexAnomalyDetail)
def detail(code: str, session: Session = Depends(db_session)) -> IndexAnomalyDetail:
    idx = index_repo.get_by_code(session, code)
    if idx is None:
        raise HTTPException(404, f"index not found: {code}")
    rows = anomaly_repo.list_for_index(session, idx.id, limit=2000)
    counts: dict[str, int] = {s: 0 for s in SEVERITIES}
    items: list[AnomalyItem] = []
    for r in rows:
        counts[r.severity] = counts.get(r.severity, 0) + 1
        items.append(AnomalyItem(
            id=r.id,
            date=r.date, field=r.field, source=r.source,
            anomaly_type=r.anomaly_type, severity=r.severity,
            value=None if r.value is None else format(r.value, "f"),
            baseline=None if r.baseline is None else format(r.baseline, "f"),
            note=r.note, detected_at=r.detected_at,
            acknowledged_at=r.acknowledged_at,
            acknowledged_note=r.acknowledged_note,
        ))
    market_code = _market_code_map(session).get(idx.market_id, "?")
    return IndexAnomalyDetail(
        code=idx.code, name=idx.name, market=market_code,
        counts=counts, anomalies=items,
    )


@router.patch("/data-quality/anomaly/{anomaly_id}", response_model=AckResponse)
def patch_anomaly_ack(
    anomaly_id: int,
    body: AckRequest,
    session: Session = Depends(db_session),
) -> AckResponse:
    """标记或取消标记一条异常为「已核对」。

    body.acknowledged=True 时记录 acknowledged_at + acknowledged_note；
    =False 时清空两个字段。"""
    row = anomaly_repo.set_acknowledged(
        session, anomaly_id, ack=body.acknowledged, note=body.note,
    )
    if row is None:
        raise HTTPException(404, f"anomaly not found: {anomaly_id}")
    session.commit()
    return AckResponse(
        id=row.id,
        acknowledged_at=row.acknowledged_at,
        acknowledged_note=row.acknowledged_note,
    )
