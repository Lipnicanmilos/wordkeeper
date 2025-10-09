# app/schemas/category.py
from pydantic import BaseModel
from typing import Optional

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    user_id: int  # PRIDAJTE TOTO

class CategoryResponse(CategoryBase):
    id: int
    user_id: int  # Zmeňte z Optional na povinné

    class Config:
        from_attributes = True