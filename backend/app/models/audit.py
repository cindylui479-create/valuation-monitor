from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DataAudit(Base):
    __tablename__ = "data_audit"
    __table_args__ = (Index("idx_audit_record", "record_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(32))
    record_key: Mapped[str] = mapped_column(String(128))
    field: Mapped[str] = mapped_column(String(32))
    old_value: Mapped[str | None] = mapped_column(String(64))
    new_value: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32))
    audit_time: Mapped[str] = mapped_column(String(32))
