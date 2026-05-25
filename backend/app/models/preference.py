from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPreference(Base):
    __tablename__ = "user_preference"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    value_json: Mapped[str] = mapped_column(String(2048))
    updated_at: Mapped[str] = mapped_column(String(32))
