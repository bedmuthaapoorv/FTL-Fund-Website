from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_static_site(app: FastAPI, static_dir: str) -> None:
    """Serves the prerendered site (web/dist) from the same origin as the
    API, so cookies stay first-party and one CSP covers everything.
    /approach -> approach.html; unknown paths get the app shell (404 status),
    whose client router renders the not-found page."""
    root = Path(static_dir).resolve()
    shell = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def site(path: str):
        if path.startswith("api/") or path == "api":
            raise HTTPException(404, "Not found.")
        path = path.strip("/")
        candidates = (path, f"{path}.html", f"{path}/index.html") if path else ("index.html",)
        for candidate in candidates:
            f = (root / candidate).resolve()
            if f.is_file() and f.is_relative_to(root) and f.name != "csp-hashes.json":
                immutable = f.is_relative_to(root / "assets")
                headers = {"Cache-Control": "public, max-age=31536000, immutable" if immutable else "no-cache"}
                return FileResponse(f, headers=headers)
        return FileResponse(shell, status_code=404, headers={"Cache-Control": "no-cache"})
