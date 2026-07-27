# syntax=docker/dockerfile:1

# Tags: 3.13-debian-dev, 3.13-debian13-dev, 3.13-dev, 3.13.14-debian-dev, 3.13.14-debian13-dev, 3.13.14-dev
FROM dhi.io/python@sha256:06bc72c5a241422a0acd47f8df7d1193af9b2969d2ffa5aa32d1cc071381b7a7 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_NO_CACHE=1

WORKDIR /app

COPY .python-version pyproject.toml uv.lock main.py utils.py ./

RUN uv sync --frozen

# Tags: 3.13, 3.13-debian, 3.13-debian13, 3.13.14, 3.13.14-debian, 3.13.14-debian13
FROM dhi.io/python@sha256:8054fc5c80a69cfbe57b7a9543c909ccf1f9cf599118a530fd2df6b1870236bc

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY main.py utils.py ./

CMD ["python", "main.py"]
