from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CloneRequest(BaseModel):
    github_url: HttpUrl


class LocalPathRequest(BaseModel):
    path: str = Field(min_length=1)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class PRRiskRequest(BaseModel):
    changed_files: list[str] = Field(default_factory=list, max_length=200)
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=2000)
    pr_url: str = Field(default="", max_length=500)
    repository: str = Field(default="", max_length=300)
    pr_number: int | None = Field(default=None, ge=1)


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    name: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=12, max_length=256)
    organization_name: str | None = Field(default=None, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class GitHubRepositoryImportRequest(BaseModel):
    clone_url: HttpUrl


class GitHubAppCallbackRequest(BaseModel):
    installation_id: str = Field(min_length=1, max_length=128)
    setup_action: str = Field(default="", max_length=64)
    state: str = Field(min_length=16, max_length=128)


class RepositoryResponse(BaseModel):
    id: str
    name: str
    source_type: str
    source: str
    status: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
