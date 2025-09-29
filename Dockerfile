FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y && apt-get clean

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /uvx /bin/

ENV HOME=/home/nobody
ENV UV_CACHE_DIR=/home/nobody/.cache

WORKDIR /home/nobody/app

COPY .python-version pyproject.toml uv.lock main.py utils.py ./

# chown is necessary to fix permission issue on cache folder when executing as nobody
RUN uv sync --frozen && chown -R nobody:nogroup /home/nobody/.cache

USER nobody

ENTRYPOINT ["uv", "run", "main.py"]
