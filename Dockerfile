FROM ghcr.io/astral-sh/uv:0.10.10 AS uv

FROM python:3.13-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 5236
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/.venv/bin/python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:5236/api/v1/health')"]

CMD ["/app/.venv/bin/python", "-m", "app"]
