from app.database.connection import Base
from sqlalchemy import Column, Integer, String, DateTime, Enum, Float, ForeignKey
from datetime import datetime
import enum

class KnowledgeLevel(enum.Enum):
    DONT_KNOW = "dont_know"
    LEARNING = "learning"
    KNOW = "know"

class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True, index=True)
    original_word = Column(String(100), nullable=False)
    translation = Column(String(100), nullable=False)
    language_from = Column(String(10), default="en")
    language_to = Column(String(10), default="sk")
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, nullable=True)
    
    # Pokročilé polia pre testovanie
    knowledge_level = Column(Enum(KnowledgeLevel, values_callable=lambda x: [e.value for e in x]), default=KnowledgeLevel.DONT_KNOW)
    times_tested = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    last_tested = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)