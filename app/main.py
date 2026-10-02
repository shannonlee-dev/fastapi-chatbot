"""FastAPI application의 공통 실행 구성을 조립한다."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles

from app.admin.router import router as admin_router
from app.auth.models import User
from app.auth.service import ensure_initial_admin
from app.chat.models import ChatExchange
from app.chat.router import router as chat_router
from app.core.config import Settings, settings
from app.core.database import SessionLocal, init_db
from app.core.http import get_exception_handlers
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.ui.router import router as ui_router

SESSION_MAX_AGE_SECONDS = 28_800
_REGISTERED_MODELS = (User, ChatExchange)
_STATIC_DIRECTORY = Path(__file__).resolve().parent / "ui" / "static"


def _create_lifespan(
    app_settings: Settings,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None, None]:
        """요청을 받기 전에 DB table과 초기 admin 계정을 준비한다."""

        init_db()
        with SessionLocal() as db:
            ensure_initial_admin(db=db, app_settings=app_settings)
        yield

    return lifespan


def _register_routes(application: FastAPI) -> None:
    """통합 Router와 resource별 허용 method를 application에 연결한다."""

    router = APIRouter()
    allowed_methods: dict[str, set[str]] = {}
    for feature_router in (admin_router, chat_router, ui_router):
        router.include_router(feature_router)
        for route in feature_router.routes:
            if isinstance(route, APIRoute):
                allowed_methods.setdefault(route.path, set()).update(
                    route.methods or ()
                )
    application.include_router(router)
    application.state.allowed_methods = allowed_methods


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """검증된 설정으로 FastAPI application을 생성한다."""

    configured = app_settings or settings
    configure_logging(log_level=configured.log_level, log_file=configured.log_file)

    application = FastAPI(
        lifespan=_create_lifespan(configured),
        exception_handlers=get_exception_handlers(),
    )
    application.state.settings = configured
    application.add_middleware(
        SessionMiddleware,
        secret_key=configured.session_secret.get_secret_value(),
        max_age=SESSION_MAX_AGE_SECONDS,
        same_site="lax",
        https_only=configured.app_env == "production",
    )
    application.add_middleware(RequestIdMiddleware)

    _register_routes(application)
    application.mount(
        "/static",
        StaticFiles(directory=_STATIC_DIRECTORY),
        name="static",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
