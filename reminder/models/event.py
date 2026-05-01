from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reminder.enums import Category, Recurrence
from reminder.models.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False)
    recurrence: Mapped[Recurrence] = mapped_column(Enum(Recurrence), nullable=False)
    next_remind_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remind_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remind_max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="events")  # type: ignore[name-defined]  # noqa: F821
    history: Mapped[list["EventHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EventHistory", back_populates="event", cascade="all, delete-orphan"
    )
