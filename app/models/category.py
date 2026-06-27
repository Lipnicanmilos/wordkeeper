from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from app.database.connection import Base
from app.utils import utcnow
from .word import Word

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Pridané
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint('name', 'user_id', name='unique_category_name_per_user'),)

    # Vzťah k používateľovi
    user = relationship("User", back_populates="categories")

    # Vzťah k slovíčkam s kaskádovým mazaním
    words = relationship("Word", backref="category", cascade="all, delete-orphan")
