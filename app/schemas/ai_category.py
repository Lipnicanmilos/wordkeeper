from pydantic import BaseModel, Field
from typing import List, Optional


class AICategoryWord(BaseModel):
    original_word: str
    translation: str
    language_from: str = "en"
    language_to: str = "sk"


class AICategoryCreateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    language_from: str = "en"
    language_to: str = "sk"
    count: int = Field(default=25, ge=5, le=200)
    ai_provider: str = Field(default="gemini")


class AICategoryCreateResponse(BaseModel):
    category_id: int
    category_name: str
    category_description: Optional[str] = None
    inserted_words: int
    skipped_words: int
    words: List[AICategoryWord]

