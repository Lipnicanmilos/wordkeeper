from app.database.connection import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship


class Payment(Base):
    """
    Záznam o platbe / predplatnom.

    Navrhnuté tak, aby sedelo na Stripe Billing aj Paddle:
      - provider: 'stripe' | 'paddle' | 'manual'
      - provider_payment_id: id transakcie u poskytovateľa (napr. Stripe PaymentIntent / Invoice id)
      - provider_subscription_id: id predplatného (ak ide o subscription)
      - status: 'succeeded' | 'pending' | 'failed' | 'refunded' | 'canceled'
      - amount: suma v základnej mene (napr. 4.99)
      - currency: ISO kód, default EUR
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # email si držíme aj redundantne, aby prehľad fungoval aj po zmazaní usera
    email = Column(String(255), nullable=True, index=True)

    provider = Column(String(20), default="stripe", nullable=False)
    provider_payment_id = Column(String(255), nullable=True, index=True)
    provider_subscription_id = Column(String(255), nullable=True, index=True)

    status = Column(String(20), default="succeeded", nullable=False, index=True)
    amount = Column(Float, default=0.0, nullable=False)
    currency = Column(String(10), default="EUR", nullable=False)

    description = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="payments")


Index("ix_payments_user_status", Payment.user_id, Payment.status)
