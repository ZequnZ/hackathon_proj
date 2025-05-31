from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    messages: list[Any]
    result: str | None = Field(default=None)
    follow_up_question: str | None = Field(default=None)


class ChatResponse(BaseModel):
    message: str | None = Field(default=None)
    result: str | None = Field(default=None)
    follow_up_question: str | None = Field(default=None)


class HealthResponse(BaseModel):
    status: str = "UP"


class ErrorResponse(BaseModel):
    DETAIL: str = "Something went wrong"
