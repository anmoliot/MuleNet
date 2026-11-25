FROM python:3.13.18-slim@sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50

WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.13.9 && python -m pip uninstall --yes pip
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project

COPY ml_service/ ./
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "serving:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--limit-concurrency", "16"]
