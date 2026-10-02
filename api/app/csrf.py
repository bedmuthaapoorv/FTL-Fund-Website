from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

SAFE = {"GET", "HEAD", "OPTIONS"}
HEADER = "x-fth-csrf"
# The sync endpoint is called by a script (HMAC-authenticated, no cookies).
EXEMPT = ("/api/sync",)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Requires a custom header on state-changing API requests. A cross-site
    form or fetch cannot set it without a CORS preflight, which this API
    never approves. Session cookies are also SameSite=Strict."""

    async def dispatch(self, request: Request, call_next):
        p = request.url.path
        if request.method not in SAFE and p.startswith("/api") and not p.startswith(EXEMPT):
            if request.headers.get(HEADER) != "1":
                return JSONResponse({"detail": "Missing CSRF header."}, status_code=403)
        return await call_next(request)
