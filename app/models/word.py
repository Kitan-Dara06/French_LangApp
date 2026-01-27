import enum

from sqlalchemy import Column, Enum, Integer, String

from app.core.database import Base


class POSType(enum.Enum):
    VERB = "verb"
    NOUN = "noun"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    OTHER = "other"


class CEFRLevel(enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True)
    text = Column(String, unique=True, nullable=False, index=True)
    part_of_speech = Column(Enum(POSType), nullable=False)
    level = Column(Enum(CEFRLevel), default=CEFRLevel.A1)
