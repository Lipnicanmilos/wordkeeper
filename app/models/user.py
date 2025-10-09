from app.database.connection import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    password = Column(String(255), nullable=False)
    is_plus = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relácie
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
