from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .ratelimit import limiter
from .csrf import CSRFMiddleware
from .headers import SecurityHeadersMiddleware
from .static_site import mount_static_site
from .routers import admin, auth, contact, investor, sync


def create_app() -> FastAPI:
    s = get_settings()
    if s.env == "prod" and (problems := s.production_problems()):
        raise RuntimeError("Refusing to start in production:\n- " + "\n- ".join(problems))
    app = FastAPI(
        title="Frontier TradeLight API",
        docs_url="/api/docs" if s.env == "dev" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if s.env == "dev" else None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    for r in (contact, auth, investor, admin, sync):
        app.include_router(r.router)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    if s.static_dir:
        mount_static_site(app, s.static_dir)  # last: catch-all route
    return app


app = create_app()
