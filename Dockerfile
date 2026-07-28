# grounded-pr-review-agent — production image (FastAPI ingress + ARQ worker share it).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Install the package with the production extras. Editable so scripts/migrations/ stays on
# disk (the migration path resolves relative to the source tree).
COPY pyproject.toml README.md ./
COPY grounded ./grounded
COPY scripts ./scripts
RUN pip install -e ".[server,data,queue,llm]"

EXPOSE 8000
# Railway/containers set $PORT; default 8000 locally.
CMD ["sh", "-c", "uvicorn grounded.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
