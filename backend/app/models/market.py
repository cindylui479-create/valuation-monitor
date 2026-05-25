from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Market(Base):
    __tablename__ = "market"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(8))
    tz: Mapped[str] = mapped_column(String(64))

    calendar: Mapped[list["TradingCalendar"]] = relationship(back_populates="market")


class TradingCalendar(Base):
    __tablename__ = "trading_calendar"
    __table_args__ = (
        UniqueConstraint("market_id", "date"),
        Index("idx_calendar_market_date", "market_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("market.id"))
    date: Mapped[str] = mapped_column(String(10))
    is_open: Mapped[bool] = mapped_column()

    market: Mapped[Market] = relationship(back_populates="calendar")
