from datetime import datetime

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.sql.sqltypes import Boolean, DateTime

from app.core.database import Base


class SessionAttempt(Base):
    __tablename__ = "session_attempts"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False, index=True)  # ← Added index
    word_id = Column(Integer, ForeignKey("words.id"))
    sentence_id = Column(Integer, ForeignKey("sentences.id"))
    user_input = Column(String)
    correct_answer = Column(String)
    is_correct = Column(Boolean)
    response_time_ms = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    error_type = Column(String, nullable=True)
    confused_with = Column(String, nullable=True)


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)  # ← ADDED THIS
    total_attempts = Column(Integer)
    correct_count = Column(Integer)

    headline = Column(Text)
    strengths = Column(JSON)
    weaknesses = Column(JSON)  # ← FIXED: was 'weakness'
    linguistic_insight = Column(Text)
    next_focus = Column(Text)
