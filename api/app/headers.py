import json
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .config import get_settings

COMMON = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"


def site_csp(static_dir: str | None) -> str:
    """CSP for the website. Inline scripts are allowed only by the exact
    hashes recorded at build time (web/scripts/csp-hashes.mjs)."""
    hashes: list[str] = []
    if static_dir and (Path(static_dir) / "csp-hashes.json").exists():
        hashes = json.loads((Path(static_dir) / "csp-hashes.json").read_text())
    return "; ".join([
        "default-src 'self'",
        "script-src 'self' " + " ".join(hashes),
        "style-src 'self'",
        "style-src-attr 'unsafe-inline'",  # React style={{}} props only (chart tooltip position)
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        s = get_settings()
        self.hsts = s.env == "prod"
        self.site_csp = site_csp(s.static_dir)
        self.dev_docs = s.env == "dev"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        for k, v in COMMON.items():
            response.headers.setdefault(k, v)
        if self.hsts:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        if path.startswith("/api"):
            if not (self.dev_docs and path.startswith("/api/docs")):
                response.headers["Content-Security-Policy"] = API_CSP
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Content-Security-Policy"] = self.site_csp
        return response
