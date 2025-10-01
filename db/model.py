from sqlalchemy import (
    Integer,
    BigInteger,
    String,
    Text,
    Index,
    Boolean,
    DateTime,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Numeric,
    func,
)
from sqlalchemy.orm import mapped_column
from datetime import datetime
from .base import Base


class Spyusers(Base):
    __tablename__ = "spyusers"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(BigInteger, nullable=False, index=True)
    username = mapped_column(String(255), nullable=True)  # Telegram @username
    user_full_name = mapped_column(String(255), nullable=True)  # Telegram First Last
    ref_id = mapped_column(BigInteger)
    bot_name = mapped_column(String(255))
    is_banned = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    language = mapped_column(String(16), nullable=True)
    agreement_accepted = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    agreement_accepted_at = mapped_column(DateTime, nullable=True)
    subscription_tier = mapped_column(String(16), nullable=False, default="free", server_default="free")
    subscription_expires_at = mapped_column(DateTime, nullable=True)
    subscription_period = mapped_column(String(16), nullable=True)
    subscription_weekly_media_count = mapped_column(Integer, nullable=False, default=0, server_default="0")
    subscription_weekly_reset_at = mapped_column(DateTime, nullable=True)
    subscription_monthly_media_count = mapped_column(Integer, nullable=False, default=0, server_default="0")
    subscription_monthly_reset_at = mapped_column(DateTime, nullable=True)
    subscription_weekly_notification_count = mapped_column(Integer, nullable=False, default=0, server_default="0")
    subscription_weekly_notification_reset_at = mapped_column(DateTime, nullable=True)
    subscription_monthly_notification_count = mapped_column(Integer, nullable=False, default=0, server_default="0")
    subscription_monthly_notification_reset_at = mapped_column(DateTime, nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    updated_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    last_seen_at = mapped_column(DateTime, nullable=True)

    # Add table arguments with index
    __table_args__ = (
        Index("idx_spyusers_user_id", "user_id"),
    )


class MessageCache(Base):
    """Table for storing cached messages."""
    __tablename__ = "message_cache"

    message_id = mapped_column(BigInteger, nullable=False)
    chat_id = mapped_column(BigInteger, nullable=False)
    user_full_name = mapped_column(String(255), nullable=False) # Ensure UTF-8 handling if not default
    text = mapped_column(Text, nullable=False) # Ensure UTF-8 handling if not default
    message_type = mapped_column(String(50), nullable=False, default="text")
    additional_info = mapped_column(Text, nullable=True) # Ensure UTF-8 handling if not default
    user_id = mapped_column(BigInteger, nullable=False)
    expires_at = mapped_column(DateTime, nullable=True)

    __table_args__ = (PrimaryKeyConstraint("chat_id", "message_id"), {})


class Webhook(Base):
    __tablename__ = "webhooks"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_id = mapped_column(BigInteger, nullable=False)
    bot_username = mapped_column(String(255), nullable=False)
    token = mapped_column(String(255), nullable=False)
    webhook_url = mapped_column(String(255), nullable=False)

    __table_args__ = (
        Index("idx_webhook_url", "webhook_url"),
    )


class CommandStat(Base):
    __tablename__ = "command_stats"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    command = mapped_column(String(64), nullable=False, unique=True)
    count = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    updated_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(BigInteger, nullable=False, index=True)
    plan = mapped_column(String(16), nullable=False)
    period = mapped_column(String(16), nullable=True)
    amount_stars = mapped_column(Integer, nullable=True)
    amount_usd = mapped_column(Numeric(10, 2), nullable=True)
    method = mapped_column(String(32), nullable=False)
    status = mapped_column(String(24), nullable=False, default="success", server_default="success")
    is_manual = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    initiator_id = mapped_column(BigInteger, nullable=True)
    created_at = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.current_timestamp())
    details = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_payments_created", "created_at"),)
