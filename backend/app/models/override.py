from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ThresholdOverride(Base):
    __tablename__ = "threshold_override"

    id: Mapped[int] = mapped_column(primary_key=True)
    index_id: Mapped[int] = mapped_column(ForeignKey("index_meta.id"), unique=True)
    boundaries_json: Mapped[str] = mapped_column(String(512))
    updated_at: Mapped[str] = mapped_column(String(32))
