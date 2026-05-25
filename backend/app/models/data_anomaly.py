from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DataAnomaly(Base):
    """SRS R11：数据异常检测记录。

    每条记录是一个 (指数, 日期, 字段, 数据源, 异常类型) 维度的告警。
    同维度重复检测时 upsert（更新 value/baseline/note/detected_at）。
    """

    __tablename__ = "data_anomaly"
    __table_args__ = (
        UniqueConstraint(
            "index_id", "date", "field", "source", "anomaly_type",
            name="uq_anomaly_dim",
        ),
        Index("idx_anomaly_index_date", "index_id", "date"),
        Index("idx_anomaly_severity_date", "severity", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    field: Mapped[str] = mapped_column(String(16))            # pe_ttm / pb / pe_ttm_csi / pb_csi
    source: Mapped[str] = mapped_column(String(8))            # 'lg' / 'csi'
    anomaly_type: Mapped[str] = mapped_column(String(24))     # NEGATIVE / DAILY_JUMP / MAD_OUTLIER / STALE / CROSS_DIVERGE / CROSS_IDENTICAL / LOW_VARIANCE
    severity: Mapped[str] = mapped_column(String(8))          # HIGH / MEDIUM / LOW / INFO
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    baseline: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    note: Mapped[str | None] = mapped_column(String(255))
    detected_at: Mapped[str] = mapped_column(String(32))
    # SRS R11：人工核对标记（NULL = 未核对；非 NULL = 已核对的 ISO 时间戳）
    acknowledged_at: Mapped[str | None] = mapped_column(String(32))
    acknowledged_note: Mapped[str | None] = mapped_column(String(255))
