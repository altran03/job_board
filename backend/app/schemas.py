from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class JobApplicationBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    date_applied: date


class JobApplicationCreate(JobApplicationBase):
    pass


class JobApplication(JobApplicationBase):
    id: int

    class Config:
        from_attributes = True


