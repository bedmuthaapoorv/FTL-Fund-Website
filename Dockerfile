# One image: FastAPI serves the API and the prerendered site from one origin.
# Host-agnostic: run behind any TLS-terminating proxy / platform.

FROM node:22-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    ENV=prod STATIC_DIR=/app/site FORWARDED_ALLOW_IPS=127.0.0.1
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY api/app ./app
COPY api/migrations ./migrations
COPY api/alembic.ini ./
COPY --from=web /web/dist ./site
USER app
EXPOSE 8000
# Set FORWARDED_ALLOW_IPS to your proxy's address so rate limits see real client IPs.
CMD alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
    --proxy-headers --forwarded-allow-ips="$FORWARDED_ALLOW_IPS"
