FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

ENV HOME=/home/nobody
ENV UV_CACHE_DIR=/home/nobody/.cache

WORKDIR /home/nobody/app

COPY pyproject.toml uv.lock main.py utils.py .python-version ./

# fix Permission error on cache folder when executing as user (nobody)
RUN uv sync --frozen && chown -R nobody:nogroup /home/nobody/.cache

USER nobody

ENTRYPOINT ["uv", "run", "main.py"]

