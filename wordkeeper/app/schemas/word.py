from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import enum

class KnowledgeLevel(str, enum.Enum):
    DONT_KNOW = "dont_know"
    LEARNING = "learning"
    KNOW = "know"

class WordBase(BaseModel):
    original_word: str
    translation: str
    category_id: int
    language_from: Optional[str] = "en"
    language_to: Optional[str] = "sk"

class WordCreate(WordBase):
    pass

class WordUpdate(BaseModel):
    original_word: Optional[str] = None
    translation: Optional[str] = None
    category_id: Optional[int] = None
    knowledge_level: Optional[KnowledgeLevel] = None

class WordResponse(WordBase):
    id: int
    user_id: Optional[int] = None
    knowledge_level: KnowledgeLevel
    times_tested: int
    times_correct: int
    last_tested: Optional[datetime] = None
    success_rate: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WordListResponse(BaseModel):
    words: List[WordResponse]
    total: int

class TestConfig(BaseModel):
    category_id: Optional[int] = None
    knowledge_levels: List[KnowledgeLevel]
    limit: int = Field(default=10, ge=1, le=1000)  # Limit between 1 and 1000
    test_direction: str = "original_to_translation"  # "original_to_translation" or "translation_to_original"

class TestResult(BaseModel):
    word_id: int
    is_correct: bool

class KnowledgeLevelUpdate(BaseModel):
    knowledge_level: KnowledgeLevel
