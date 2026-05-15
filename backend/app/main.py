from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.api.oauth import router as oauth_router
from app.api.todo import router as todo_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.scheduler import build_scheduler, schedule_sync_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(debug=settings.debug)
    log = get_logger("startup")
    log.info("home_agent.start", env=settings.environment)

    scheduler = build_scheduler()
    schedule_sync_job(scheduler)
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)
    log.info("home_agent.stop")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(todo_router)
    app.include_router(chat_router)
    app.include_router(events_router)
    app.include_router(oauth_router)
    return app


app = create_app()
