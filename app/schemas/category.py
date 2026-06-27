# app/schemas/category.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict
from datetime import datetime

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    user_id: int  # PRIDAJTE TOTO

class CategoryUpdate(CategoryBase):
    pass  # rovnaké polia ako CategoryBase

class CategoryResponse(CategoryBase):
    id: int
    user_id: int  # Zmeňte z Optional na povinné
    created_at: Optional[datetime] = None
    total_words: int = 0
    level_counts: Dict[str, int] = {}  # počty pre každý level
    level_percentages: Dict[str, float] = {}  # percentá pre každý level

    model_config = ConfigDict(from_attributes=True)
