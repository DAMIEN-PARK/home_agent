from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.todo import Project, Task, TaskContext


class NotFoundError(LookupError):
    pass


class TodoService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    # ---- Projects ----------------------------------------------------------

    async def list_projects(self, *, include_archived: bool = False) -> list[Project]:
        stmt = select(Project).where(Project.user_id == self.user_id)
        if not include_archived:
            stmt = stmt.where(Project.archived_at.is_(None))
        stmt = stmt.order_by(Project.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

    async def create_project(self, *, name: str, description: str | None) -> Project:
        project = Project(user_id=self.user_id, name=name, description=description)
        self.session.add(project)
        await self.session.flush()
        return project

    async def update_project(
        self,
        project_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        archived: bool | None = None,
    ) -> Project:
        project = await self._get_project(project_id)
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if archived is not None:
            project.archived_at = datetime.now(timezone.utc) if archived else None
        await self.session.flush()
        return project

    async def delete_project(self, project_id: UUID) -> None:
        project = await self._get_project(project_id)
        await self.session.delete(project)

    async def _get_project(self, project_id: UUID) -> Project:
        project = await self.session.get(Project, project_id)
        if project is None or project.user_id != self.user_id:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    # ---- Contexts ----------------------------------------------------------

    async def list_contexts(self) -> list[TaskContext]:
        stmt = (
            select(TaskContext)
            .where(TaskContext.user_id == self.user_id)
            .order_by(TaskContext.name.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    async def create_context(self, *, name: str) -> TaskContext:
        ctx = TaskContext(user_id=self.user_id, name=name)
        self.session.add(ctx)
        await self.session.flush()
        return ctx

    # ---- Tasks -------------------------------------------------------------

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        project_id: UUID | None = None,
        context_id: UUID | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if project_id is not None:
            stmt = stmt.where(Task.project_id == project_id)
        if context_id is not None:
            stmt = stmt.where(Task.context_id == context_id)
        stmt = stmt.order_by(Task.priority.asc(), Task.due_at.asc().nulls_last(), Task.created_at.desc())
        return list((await self.session.scalars(stmt)).all())

    async def get_task(self, task_id: UUID) -> Task:
        task = await self.session.get(Task, task_id)
        if task is None or task.user_id != self.user_id:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    async def create_task(
        self,
        *,
        title: str,
        notes: str | None = None,
        project_id: UUID | None = None,
        context_id: UUID | None = None,
        priority: int = 3,
        due_at: datetime | None = None,
    ) -> Task:
        task = Task(
            user_id=self.user_id,
            title=title,
            notes=notes,
            project_id=project_id,
            context_id=context_id,
            priority=priority,
            due_at=due_at,
            status="open",
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_task(
        self,
        task_id: UUID,
        *,
        title: str | None = None,
        notes: str | None = None,
        project_id: UUID | None = None,
        context_id: UUID | None = None,
        status: str | None = None,
        priority: int | None = None,
        due_at: datetime | None = None,
    ) -> Task:
        task = await self.get_task(task_id)
        if title is not None:
            task.title = title
        if notes is not None:
            task.notes = notes
        if project_id is not None:
            task.project_id = project_id
        if context_id is not None:
            task.context_id = context_id
        if priority is not None:
            task.priority = priority
        if due_at is not None:
            task.due_at = due_at
        if status is not None:
            task.status = status
            task.completed_at = (
                datetime.now(timezone.utc) if status == "done" else None
            )
        await self.session.flush()
        return task

    async def complete_task(self, task_id: UUID) -> Task:
        return await self.update_task(task_id, status="done")

    async def delete_task(self, task_id: UUID) -> None:
        task = await self.get_task(task_id)
        await self.session.delete(task)
