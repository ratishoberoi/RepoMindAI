from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CloneRequest(BaseModel):
    github_url: HttpUrl


class LocalPathRequest(BaseModel):
    path: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class RepositoryResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source: str
    status: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]

