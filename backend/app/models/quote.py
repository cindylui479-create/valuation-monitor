from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IndexQuote(Base):
    __tablename__ = "index_quote"
    __table_args__ = (
        UniqueConstraint("index_id", "date"),
        Index("idx_quote_index_date", "index_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"))
    date: Mapped[str] = mapped_column(String(10))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    pe_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))      # 主源（LG 优先；3 只综合指数 = Tushare）
    pb: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    # SRS R10：CSI 口径并存（仅 Tushare 覆盖的 6 只指数有）
    pe_ttm_csi: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    pb_csi: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    earnings_growth_3y: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    ma50: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ma200: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    northbound_60d_pct: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    source: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[str] = mapped_column(String(32))
