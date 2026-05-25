from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Valuation(Base):
    __tablename__ = "valuation"
    __table_args__ = (
        # SRS R10：source 维度区分 lg / csi 双口径
        UniqueConstraint("index_id", "date", "window", "source"),
        Index("idx_valuation_index_date_window", "index_id", "date", "window"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    window: Mapped[str] = mapped_column(String(8))              # 5y / 10y / all
    source: Mapped[str] = mapped_column(String(8), default="lg") # lg / csi
    pe_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    pb_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    dy_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    tier: Mapped[str | None] = mapped_column(String(16))
    # SRS R12+：温度来源标识
    # pe_10y / pe_all  — 基于 PE-TTM 历史百分位（默认）
    # price_10y / price_all — 基于 close 历史百分位（PE 数据不足时 fallback；与基金 NAV 自比同思路）
    # null — 数据不足
    temperature_source: Mapped[str | None] = mapped_column(String(16))
    # close 历史百分位（fallback 路径产出；正常路径也填，UI 可参考）
    close_percentile: Mapped[Decimal | None] = mapped_column(Numeric(10, 8))
    computed_at: Mapped[str] = mapped_column(String(32))
