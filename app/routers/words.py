from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import pandas as pd
import io

from app.database.connection import get_db
from app.models.user import User
from app.models.category import Category
from app.models.word import Word, KnowledgeLevel
from app.schemas.word import (
    WordCreate, WordResponse, WordUpdate, WordListResponse,
    TestConfig, TestResult, KnowledgeLevel, KnowledgeLevelUpdate
)

router = APIRouter(prefix="/api/v1/words", tags=["words"])

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Získa aktuálneho používateľa zo session"""
    user_session = request.session.get('user')
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_session['id']).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

# ZÁKLADNÉ CRUD OPERÁCIE
@router.post("/", response_model=WordResponse)
def create_word(
    word_data: WordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vytvorí nové slovíčko"""
    # Skontrolujte či kategória existuje
    category = db.query(Category).filter(Category.id == word_data.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Vytvorte nové slovíčko
    new_word = Word(
        original_word=word_data.original_word,
        translation=word_data.translation,
        category_id=word_data.category_id,
        language_from=word_data.language_from,
        language_to=word_data.language_to,
        user_id=current_user.id if current_user else None  # Ak máte user systém
    )
    
    db.add(new_word)
    db.commit()
    db.refresh(new_word)
    
    return create_word_response(new_word)

@router.get("/", response_model=WordListResponse)
def get_words(
    request: Request,
    category_id: Optional[int] = Query(None, description="Filter by category"),
    knowledge_level: Optional[KnowledgeLevel] = Query(None, description="Filter by knowledge level"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Získa zoznam slovíčok s filtrami"""
    query = db.query(Word)
    
    # Filtre
    if category_id:
        query = query.filter(Word.category_id == category_id)
    
    if knowledge_level:
        query = query.filter(Word.knowledge_level == knowledge_level)
    
    # Ak máte user systém, pridajte filter podľa usera
    # if current_user:
    #     query = query.filter(Word.user_id == current_user.id)
    
    total = query.count()
    words = query.offset(skip).limit(limit).all()
    
    return WordListResponse(
        words=[create_word_response(word) for word in words],
        total=total
    )

@router.get("/{word_id}", response_model=WordResponse)
def get_word(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Získa konkrétne slovíčko"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    # Overiť vlastníctvo ak máte user systém
    # if current_user and word.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    return create_word_response(word)

@router.put("/{word_id}", response_model=WordResponse)
def update_word(
    word_id: int,
    word_data: WordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aktualizuje slovíčko"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    # Overiť vlastníctvo ak máte user systém
    # if current_user and word.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    # Aktualizovať polia
    update_data = word_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(word, field, value)
    
    word.updated_at = datetime.now()
    db.commit()
    db.refresh(word)
    
    return create_word_response(word)

@router.delete("/{word_id}")
def delete_word(
    word_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Zmaze slovíčko"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    # Overiť vlastníctvo ak máte user systém
    # if current_user and word.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(word)
    db.commit()
    
    return {"message": "Word deleted successfully"}

# POKROČILÉ FUNKCIE
@router.put("/{word_id}/knowledge-level", response_model=WordResponse)
def update_knowledge_level(
    word_id: int,
    knowledge_level_data: KnowledgeLevelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aktualizuje úroveň znalosti slovíčka"""
    word = db.query(Word).filter(Word.id == word_id).first()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    # Overiť vlastníctvo ak máte user systém
    # if current_user and word.user_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    word.knowledge_level = knowledge_level_data.knowledge_level
    word.updated_at = datetime.now()
    db.commit()
    db.refresh(word)
    
    return create_word_response(word)

@router.post("/test/start", response_model=List[WordResponse])
def start_test(
    test_config: TestConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Začína test so slovíčkami podľa konfigurácie"""
    query = db.query(Word)
    
    # Filtre podľa konfigurácie
    if test_config.knowledge_levels:
        query = query.filter(Word.knowledge_level.in_(test_config.knowledge_levels))
    
    if test_config.category_id:
        # Overiť, že kategória existuje
        category = db.query(Category).filter(Category.id == test_config.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        query = query.filter(Word.category_id == test_config.category_id)
    
    # Zoradiť podľa úrovne znalostí a posledného testovania
    words = query.order_by(
        Word.knowledge_level,
        Word.last_tested.asc()  # Najprv slová ktoré boli testované najdlhšie
    ).limit(test_config.limit).all()
    
    if not words:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No words found for test with given criteria"
        )
    
    return [create_word_response(word) for word in words]

@router.post("/test/submit")
def submit_test_results(
    results: List[TestResult],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Spracuje výsledky testu a aktualizuje štatistiky slovíčok"""
    updated_words = []
    
    for result in results:
        word = db.query(Word).filter(Word.id == result.word_id).first()
        
        if word:
            # Aktualizovať štatistiky
            word.times_tested += 1
            if result.is_correct:
                word.times_correct += 1
                
                # Automaticky zvýšiť úroveň ak je úspešnosť vysoká
                success_rate = word.times_correct / word.times_tested
                if success_rate >= 0.8:  # 80% úspešnosť
                    if word.knowledge_level == KnowledgeLevel.DONT_KNOW:
                        word.knowledge_level = KnowledgeLevel.LEARNING
                    elif word.knowledge_level == KnowledgeLevel.LEARNING:
                        word.knowledge_level = KnowledgeLevel.KNOW
                    # KNOW level is the highest - no further promotion
            else:
                # Znížiť úroveň ak je odpoveď nesprávna
                if word.knowledge_level == KnowledgeLevel.KNOW:
                    word.knowledge_level = KnowledgeLevel.LEARNING
            
            word.last_tested = datetime.now()
            word.updated_at = datetime.now()
            updated_words.append(create_word_response(word))
    
    db.commit()
    
    return {
        "message": f"Test results processed for {len(updated_words)} words",
        "updated_words": updated_words
    }

@router.get("/stats/category/{category_id}")
def get_category_stats(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Získa štatistiky slovíčok v kategórii"""
    # Overiť, že kategória existuje
    category = db.query(Category).filter(Category.id == category_id).first()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    words = db.query(Word).filter(Word.category_id == category_id).all()
    
    total_words = len(words)
    if total_words == 0:
        return {
            "category_id": category_id,
            "category_name": category.name,
            "total_words": 0,
            "knowledge_levels": {},
            "average_success_rate": 0
        }
    
    # Počty podľa úrovní znalostí
    level_counts = {
        level.value: 0 for level in KnowledgeLevel
    }
    
    total_success = 0
    total_tested = 0
    
    for word in words:
        level_counts[word.knowledge_level.value] += 1
        total_success += word.times_correct
        total_tested += word.times_tested
    
    average_success_rate = total_success / total_tested if total_tested > 0 else 0
    
    return {
        "category_id": category_id,
        "category_name": category.name,
        "total_words": total_words,
        "knowledge_levels": level_counts,
        "average_success_rate": round(average_success_rate * 100, 2)  # v percentách
    }

@router.post("/import")
def import_words(
    request: Request,
    excelFile: UploadFile = File(...),
    category_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Importuje slovíčka z Excel súboru"""
    # Overiť, že kategória existuje
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Skontrolovať typ súboru
    if not excelFile.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are allowed"
        )

    try:
        # Načítať Excel súbor
        contents = excelFile.file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # Skontrolovať štruktúru súboru
        if len(df.columns) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Excel file must have at least 2 columns"
            )

        imported_count = 0
        errors = []

        # Spracovať každý riadok
        for index, row in df.iterrows():
            try:
                # Predpokladáme, že prvý stĺpec je anglické slovo, druhý slovenský preklad
                original_word = str(row.iloc[0]).strip()
                translation = str(row.iloc[1]).strip()

                # Preskočiť prázdne riadky
                if not original_word or not translation:
                    continue

                # Skontrolovať, či slovíčko už existuje v tejto kategórii
                existing_word = db.query(Word).filter(
                    Word.category_id == category_id,
                    Word.original_word == original_word
                ).first()

                if existing_word:
                    # Aktualizovať existujúce slovíčko
                    existing_word.translation = translation
                    existing_word.updated_at = datetime.now()
                else:
                    # Vytvoriť nové slovíčko
                    new_word = Word(
                        original_word=original_word,
                        translation=translation,
                        category_id=category_id,
                        language_from="en",  # Predpokladáme angličtinu
                        language_to="sk",    # Predpokladáme slovenčinu
                        user_id=current_user.id if current_user else None
                    )
                    db.add(new_word)

                imported_count += 1

            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")

        db.commit()

        return {
            "message": f"Successfully imported {imported_count} words",
            "imported_count": imported_count,
            "errors": errors if errors else None
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing Excel file: {str(e)}"
        )

def create_word_response(word: Word) -> WordResponse:
    """Pomocná funkcia pre vytvorenie WordResponse"""
    success_rate = word.times_correct / word.times_tested if word.times_tested > 0 else 0
    
    return WordResponse(
        id=word.id,
        original_word=word.original_word,
        translation=word.translation,
        language_from=word.language_from,
        language_to=word.language_to,
        category_id=word.category_id,
        user_id=word.user_id,
        knowledge_level=word.knowledge_level,
        times_tested=word.times_tested,
        times_correct=word.times_correct,
        last_tested=word.last_tested,
        success_rate=round(success_rate * 100, 2),  # v percentách
        created_at=word.created_at,
        updated_at=word.updated_at
    )