from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    consultation_id: str
    original_text: str
    edited_text: str | None = None
    language: str | None = None
    processing_status: str
    error_message: str | None = None
    is_mock: bool = False
    created_at: datetime
    updated_at: datetime


class TranscriptUpdateRequest(BaseModel):
    edited_text: str = Field(..., min_length=1, max_length=50000)
    language: str | None = Field(default=None, max_length=32)
