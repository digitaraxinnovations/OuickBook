"""
Application entry point.

Run locally with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError


def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    """Turn any AppError raised by a service into a clean JSON response."""
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


def create_app() -> FastAPI:
    app = FastAPI(title=f"{settings.app_name} API", debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, handle_app_error)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
