from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class UserWordMemory(Base):
    __tablename__ = "user_word_memory"

    id = Column(Integer, primary_key=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    strength: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    success_streak = Column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    next_review_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
