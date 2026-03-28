from sqlalchemy import Column, Integer, DateTime, Boolean, String, Index, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)

    payment_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=False)
    token = Column(String, nullable=False)

    __table_args__ = (
        Index(
            "idx_check_subscription",
            "user_id",
            "token",
            postgresql_where=(is_active == True)
        ),

        Index(
            "idx_check_validate_user",
            "user_id",
            postgresql_where=(is_active == True)
        ),

        Index(
            "idx_extend_subscription",
            "user_id",
            "expiration_date",
            postgresql_where=(is_active == True)
        ),
    )