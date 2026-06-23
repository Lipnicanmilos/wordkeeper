from app.database.connection import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func


class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=True)
    email = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    page = Column(String(255), nullable=True)        # z ktorej stránky bol dotaz odoslaný
    user_agent = Column(String(400), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
