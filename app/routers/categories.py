# routers/categories.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.database import get_db
from models.category import Category as CategoryModel
from schemas.category import Category, CategoryCreate

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

# Dočasné úložisko ak ešte nemáte databázu
temp_categories_db = []

@router.get("/", response_model=List[Category])
async def get_categories():
    """Získaj všetky kategórie"""
    return temp_categories_db

@router.post("/", response_model=Category)
async def create_category(category: CategoryCreate):
    """Vytvor novú kategóriu"""
    new_id = len(temp_categories_db) + 1
    new_category = Category(
        id=new_id,
        name=category.name,
        description=category.description
    )
    temp_categories_db.append(new_category.dict())
    return new_category

@router.get("/{category_id}", response_model=Category)
async def get_category(category_id: int):
    """Získaj konkrétnu kategóriu"""
    for category in temp_categories_db:
        if category["id"] == category_id:
            return category
    raise HTTPException(status_code=404, detail="Category not found")

@router.delete("/{category_id}")
async def delete_category(category_id: int):
    """Zmaz kategóriu"""
    global temp_categories_db
    for i, category in enumerate(temp_categories_db):
        if category["id"] == category_id:
            temp_categories_db.pop(i)
            return {"message": "Category deleted successfully"}
    raise HTTPException(status_code=404, detail="Category not found")