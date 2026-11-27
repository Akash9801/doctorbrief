import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import auth, consultations, dashboard, notes, patients
from app.config import get_settings
from app.database.session import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("doctorbrief.api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Voice-first clinical documentation assistant API for doctors and clinics.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = " -> ".join(str(part) for part in err.get("loc", []) if part != "body")
            msg = err.get("msg", "Invalid input")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "; ".join(errors) or "Invalid request payload."},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(_request: Request, exc: SQLAlchemyError):
        logger.error("Database error encountered: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "A database service error occurred. Please try again."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.error("Unhandled server exception: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected internal error occurred. Please try again."},
        )

    @app.get("/health", tags=["Health"])
    def health_check():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except SQLAlchemyError:
            db_status = "unavailable"
        return {"status": "ok" if db_status == "connected" else "degraded", "database": db_status}

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(patients.router)
    app.include_router(consultations.router)
    app.include_router(notes.router)

    return app


app = create_app()


def init_db_for_dev() -> None:
    """Create tables if running against a fresh local SQLite database."""
    Base.metadata.create_all(bind=engine)
