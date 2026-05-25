"""SRS v1.3.0 E：Tushare API 调用日志（每日聚合）。"""
from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TushareCallLog(Base):
    """按 (日期, 接口) 聚合每天的调用次数 + 失败次数。

    每次调用 Tushare API 时 upsert（incrementing）此表。
    用于配额监控：2000 积分用户 200 次/分 + 部分接口月度积分限额。
    """

    __tablename__ = "tushare_call_log"
    __table_args__ = (
        UniqueConstraint("call_date", "interface"),
        Index("idx_tushare_call_date", "call_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    call_date: Mapped[str] = mapped_column(String(10))         # YYYY-MM-DD
    interface: Mapped[str] = mapped_column(String(32))         # daily_basic / index_weight / ...
    n_calls: Mapped[int] = mapped_column(Integer, default=0)
    n_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error_message: Mapped[str | None] = mapped_column(String(255))
    last_called_at: Mapped[str] = mapped_column(String(32))
