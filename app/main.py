"""FastAPI application entry point and static frontend host."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import Settings, load_settings
from app.services.prediction_service import PredictionService
from app.services.property_service import PropertyService


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI modular monolith application."""
    settings = custom_settings or load_settings()

    if not settings.frontend_dir.exists():
        raise RuntimeError(
            f"Frontend directory not found at '{settings.frontend_dir}'. "
            "Set FRONTEND_DIR or ensure frontend/ exists."
        )

    property_service = PropertyService(settings.data_file_path)
    prediction_service = PredictionService(
        model=None,
        model_version=settings.model_version,
    )

    @asynccontextmanager
    async def lifespan(fastapi_app: FastAPI):
        # Future hook: load ML model artifact configured via settings.model_path.
        yield

    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Simple modular-monolith House Price Prediction API and web interface.",
        lifespan=lifespan,
    )

    application.state.settings = settings
    application.state.property_service = property_service
    application.state.prediction_service = prediction_service

    application.include_router(api_router)
    application.mount(
        "/static",
        StaticFiles(directory=str(settings.frontend_dir)),
        name="static",
    )

    index_file = settings.frontend_dir / "index.html"
    if not index_file.exists():
        raise RuntimeError(f"Frontend entry page not found at '{index_file}'.")

    @application.get("/", include_in_schema=False)
    def serve_frontend() -> FileResponse:
        return FileResponse(index_file)

    return application


app = create_app()
