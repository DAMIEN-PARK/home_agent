from uuid import UUID

from pydantic import BaseModel


class TodoistSyncResponse(BaseModel):
    synced: int
    pushed: int
    tombstoned: int
    errors: int
    pending_task_ids: list[UUID]
