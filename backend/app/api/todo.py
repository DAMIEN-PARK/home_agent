from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_default_user_id
from app.api.schemas.todo import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    TaskContextCreate,
    TaskContextOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.db.session import get_session
from app.services.todo import NotFoundError, TodoService

router = APIRouter(prefix="/todo", tags=["todo"])


def _service(session: AsyncSession, user_id: UUID) -> TodoService:
    return TodoService(session, user_id)


# ---- Projects ---------------------------------------------------------------


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    return await _service(session, user_id).list_projects(include_archived=include_archived)


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    project = await _service(session, user_id).create_project(
        name=payload.name, description=payload.description
    )
    await session.commit()
    await session.refresh(project)
    return project


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    svc = _service(session, user_id)
    try:
        project = await svc.update_project(
            project_id,
            name=payload.name,
            description=payload.description,
            archived=payload.archived,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    svc = _service(session, user_id)
    try:
        await svc.delete_project(project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await session.commit()


# ---- Contexts ---------------------------------------------------------------


@router.get("/contexts", response_model=list[TaskContextOut])
async def list_contexts(
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    return await _service(session, user_id).list_contexts()


@router.post("/contexts", response_model=TaskContextOut, status_code=status.HTTP_201_CREATED)
async def create_context(
    payload: TaskContextCreate,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    ctx = await _service(session, user_id).create_context(name=payload.name)
    await session.commit()
    await session.refresh(ctx)
    return ctx


# ---- Tasks ------------------------------------------------------------------


@router.get("/tasks", response_model=list[TaskOut])
async def list_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = Query(default=None),
    context_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    return await _service(session, user_id).list_tasks(
        status=status_filter, project_id=project_id, context_id=context_id
    )


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    task = await _service(session, user_id).create_task(
        title=payload.title,
        notes=payload.notes,
        project_id=payload.project_id,
        context_id=payload.context_id,
        priority=payload.priority,
        due_at=payload.due_at,
    )
    await session.commit()
    await session.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    try:
        return await _service(session, user_id).get_task(task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    try:
        task = await _service(session, user_id).update_task(
            task_id,
            title=payload.title,
            notes=payload.notes,
            project_id=payload.project_id,
            context_id=payload.context_id,
            status=payload.status,
            priority=payload.priority,
            due_at=payload.due_at,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await session.commit()
    await session.refresh(task)
    return task


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    try:
        task = await _service(session, user_id).complete_task(task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    session: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_default_user_id),
):
    try:
        await _service(session, user_id).delete_task(task_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await session.commit()
