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
    dark_mode = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    # Predplatné (Paddle)
    plus_expires_at = Column(DateTime, nullable=True)          # dokedy má PLUS prístup
    plus_plan = Column(String(20), nullable=True)             # monthly / annual
    plus_status = Column(String(20), nullable=True)           # trialing/active/past_due/canceled/expired
    plus_cancelled_at = Column(DateTime, nullable=True)
    paddle_customer_id = Column(String(64), nullable=True)     # Paddle customer id (ctm_...)
    paddle_subscription_id = Column(String(64), nullable=True) # Paddle subscription id (sub_...)
    # Relácie
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")