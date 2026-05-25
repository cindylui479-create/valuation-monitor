from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class IndexMeta(Base):
    __tablename__ = "index_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    category: Mapped[str] = mapped_column(String(16))             # 宽基/行业/主题
    industry_raw: Mapped[str | None] = mapped_column(String(64))
    data_source: Mapped[str] = mapped_column(String(32))
    history_start_date: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(default=True)

    funds: Mapped[list["Fund"]] = relationship(back_populates="tracks_index")


class Fund(Base):
    __tablename__ = "fund"
    __table_args__ = (Index("idx_fund_tracks", "tracks_index_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16))                 # ETF / OPEN_FUND（场内/场外形态）
    # SRS R12 §11.3.2 M7-B：估值口径细分
    fund_type: Mapped[str] = mapped_column(String(16), default="ETF")  # ETF / INDEX_FUND / ACTIVE_FUND
    tracks_index_id: Mapped[int | None] = mapped_column(ForeignKey("index_meta.id"))  # ACTIVE_FUND 时为空
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    fee_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    tracking_error_note: Mapped[str | None] = mapped_column(String(256))
    setup_date: Mapped[str | None] = mapped_column(String(10))    # 成立日（主动基金估值的起点）
    fund_manager: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(default=True)

    tracks_index: Mapped[IndexMeta | None] = relationship(back_populates="funds")
