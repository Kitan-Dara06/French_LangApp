import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text

from app.core.database import Base


class SourceType(enum.Enum):
    TATOEBA = "tatoeba"
    LLM = "llm"
    MANUAL = "manual"


class Sentence(Base):
    __tablename__ = "sentences"

    id = Column(Integer, primary_key=True)
    text = Column(String, nullable=False)
    blanked_text = Column(String, nullable=False)
    target_word_id = Column(Integer, ForeignKey("words.id"))
    tense = Column(String, nullable=True)
    source = Column(Enum(SourceType), default=SourceType.MANUAL)
    english_translation = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
