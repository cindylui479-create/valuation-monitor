from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Signal(Base):
    __tablename__ = "signal"
    __table_args__ = (
        # SRS R10：source 维度（lg/csi）允许双口径信号并存
        UniqueConstraint("index_id", "date", "source"),
        Index("idx_signal_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    source: Mapped[str] = mapped_column(String(8), default="lg")
    direction: Mapped[str] = mapped_column(String(16))
    tier: Mapped[str] = mapped_column(String(16))
    temperature: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    generated_at: Mapped[str] = mapped_column(String(32))
