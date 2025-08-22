from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .models import ApplicationStatus


class JobApplicationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    date_applied: date


class JobApplicationCreate(JobApplicationBase):
    pass


class JobApplicationUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    date_applied: Optional[date] = None
    status: Optional[ApplicationStatus] = None


class JobApplication(JobApplicationBase):
    id: int
    status: ApplicationStatus

    class Config:
        from_attributes = True


