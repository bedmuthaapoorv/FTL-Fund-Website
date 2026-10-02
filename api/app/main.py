from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .ratelimit import limiter
from .routers import contact


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="Frontier TradeLight API",
        docs_url="/api/docs" if s.env == "dev" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.env == "dev" else None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(contact.router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
