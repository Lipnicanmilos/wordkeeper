# app/database/connection.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wordkeeper.db")

# Create engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Enable foreign keys for SQLite
if "sqlite" in DATABASE_URL:
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.commit()

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Funkcia pre získanie DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()