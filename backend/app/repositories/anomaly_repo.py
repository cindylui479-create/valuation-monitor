"""SRS R11：data_anomaly 表读写。"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import DataAnomaly
from app.utils.time_utils import now_iso


def upsert(
    session: Session,
    *,
    index_id: int,
    date_: str,
    field: str,
    source: str,
    anomaly_type: str,
    severity: str,
    value: Decimal | None,
    baseline: Decimal | None,
    note: str | None,
) -> bool:
    """按 (index_id, date, field, source, anomaly_type) 去重 upsert。

    新插入返回 True；已存在则刷新 value/baseline/note/detected_at 返回 False。
    """
    existing = session.scalar(
        select(DataAnomaly).where(
            DataAnomaly.index_id == index_id,
            DataAnomaly.date == date_,
            DataAnomaly.field == field,
            DataAnomaly.source == source,
            DataAnomaly.anomaly_type == anomaly_type,
        )
    )
    if existing is not None:
        existing.value = value
        existing.baseline = baseline
        existing.note = note
        existing.severity = severity
        existing.detected_at = now_iso()
        return False
    session.add(
        DataAnomaly(
            index_id=index_id,
            date=date_,
            field=field,
            source=source,
            anomaly_type=anomaly_type,
            severity=severity,
            value=value,
            baseline=baseline,
            note=note,
            detected_at=now_iso(),
        )
    )
    return True


def list_for_index(session: Session, index_id: int, limit: int = 500) -> list[DataAnomaly]:
    return list(
        session.scalars(
            select(DataAnomaly)
            .where(DataAnomaly.index_id == index_id)
            .order_by(DataAnomaly.date.desc(), DataAnomaly.severity.desc())
            .limit(limit)
        )
    )


def counts_by_index_severity(
    session: Session, *, include_acknowledged: bool = True
) -> dict[int, dict[str, int]]:
    """返回 {index_id: {HIGH: n, MEDIUM: n, LOW: n, INFO: n}}。

    include_acknowledged=False 时排除已核对的异常。
    """
    stmt = (
        select(DataAnomaly.index_id, DataAnomaly.severity, func.count(DataAnomaly.id))
        .group_by(DataAnomaly.index_id, DataAnomaly.severity)
    )
    if not include_acknowledged:
        stmt = stmt.where(DataAnomaly.acknowledged_at.is_(None))
    out: dict[int, dict[str, int]] = {}
    for index_id, severity, n in session.execute(stmt).all():
        out.setdefault(index_id, {})[severity] = int(n)
    return out


def counts_acknowledged_by_index(session: Session) -> dict[int, int]:
    """返回 {index_id: acknowledged_count}。"""
    stmt = (
        select(DataAnomaly.index_id, func.count(DataAnomaly.id))
        .where(DataAnomaly.acknowledged_at.is_not(None))
        .group_by(DataAnomaly.index_id)
    )
    return {ix: int(n) for ix, n in session.execute(stmt).all()}


def get(session: Session, anomaly_id: int) -> DataAnomaly | None:
    return session.scalar(select(DataAnomaly).where(DataAnomaly.id == anomaly_id))


def set_acknowledged(
    session: Session, anomaly_id: int, *, ack: bool, note: str | None = None
) -> DataAnomaly | None:
    row = get(session, anomaly_id)
    if row is None:
        return None
    if ack:
        row.acknowledged_at = now_iso()
        row.acknowledged_note = note
    else:
        row.acknowledged_at = None
        row.acknowledged_note = None
    return row


def latest_anomaly_date_by_index(session: Session) -> dict[int, str]:
    stmt = (
        select(DataAnomaly.index_id, func.max(DataAnomaly.date))
        .group_by(DataAnomaly.index_id)
    )
    return {ix: d for ix, d in session.execute(stmt).all()}


def delete_for_index(session: Session, index_id: int) -> int:
    """清空一个指数的所有异常记录（重新跑全量审计前用）。"""
    res = session.execute(delete(DataAnomaly).where(DataAnomaly.index_id == index_id))
    return int(res.rowcount or 0)


def recent_by_severity(session: Session, severity: str, limit: int = 50) -> list[DataAnomaly]:
    return list(
        session.scalars(
            select(DataAnomaly)
            .where(DataAnomaly.severity == severity)
            .order_by(DataAnomaly.detected_at.desc())
            .limit(limit)
        )
    )
