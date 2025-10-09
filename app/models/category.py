from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database.connection import Base
from .word import Word

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Pridané
    
    # Vzťah k používateľovi
    user = relationship("User", back_populates="categories")

    # Vzťah k slovíčkam s kaskádovým mazaním
    words = relationship("Word", backref="category", cascade="all, delete-orphan")
