from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from .db import Base


class ApplicationStatus(enum.Enum):
    APPLIED = "Applied"
    INTERVIEW_SCHEDULED = "Interview Scheduled"
    INTERVIEW_COMPLETED = "Interview Completed"
    ONLINE_ASSESSMENT = "Online Assessment"
    REJECTED = "Rejected"
    OFFER = "Offer"
    ACCEPTED = "Accepted"
    WITHDRAWN = "Withdrawn"


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    date_applied: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), 
        default=ApplicationStatus.APPLIED,
        nullable=False
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=True)  # Email subject for duplicate detection


