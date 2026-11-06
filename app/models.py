from datetime import datetime, date
from sqlalchemy import BigInteger, String, Date, DateTime, ForeignKey, Integer, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
    monthly_limit: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UserActivity(Base):
    """Minimal activity state for opt-in style, low-frequency helpful nudges."""
    __tablename__ = "user_activity"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_inactivity_nudge_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_due_nudge_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_budget_nudge_on: Mapped[date | None] = mapped_column(Date, nullable=True)

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_tx_user_date", "user_id", "occurred_on"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    amount: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[str] = mapped_column(String(80), default="Boshqa")
    note: Mapped[str] = mapped_column(String(300), default="")
    occurred_on: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Debt(Base):
    __tablename__ = "debts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    original_amount: Mapped[int] = mapped_column(BigInteger)
    remaining: Mapped[int] = mapped_column(BigInteger)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DebtPayment(Base):
    __tablename__ = "debt_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    debt_id: Mapped[int] = mapped_column(ForeignKey("debts.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(String(300))
    remind_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
