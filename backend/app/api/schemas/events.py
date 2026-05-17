from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    source: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None

    @field_serializer("start_at", "end_at")
    def _serialize_dt(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None


class EventsResponse(BaseModel):
    events: list[EventOut]
