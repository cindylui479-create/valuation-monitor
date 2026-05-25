from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import DataAudit
from app.utils.time_utils import now_iso


def log_change(
    session: Session,
    table: str,
    record_key: str,
    field: str,
    old_value: str | None,
    new_value: str | None,
    source: str,
) -> None:
    session.add(
        DataAudit(
            table_name=table,
            record_key=record_key,
            field=field,
            old_value=old_value,
            new_value=new_value,
            source=source,
            audit_time=now_iso(),
        )
    )
