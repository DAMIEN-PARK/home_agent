from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = str  # open / done / deferred / cancelled


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    archived: bool | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskContextCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class TaskContextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    notes: str | None = None
    project_id: UUID | None = None
    context_id: UUID | None = None
    priority: int = Field(default=3, ge=1, le=5)
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None
    project_id: UUID | None = None
    context_id: UUID | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    due_at: datetime | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    notes: str | None
    project_id: UUID | None
    context_id: UUID | None
    status: TaskStatus
    priority: int
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
