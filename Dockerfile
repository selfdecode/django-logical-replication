FROM python:3.12-slim

WORKDIR /app

# Install git (needed for git dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Python dependencies
COPY uv.lock uv.lock
COPY pyproject.toml pyproject.toml
RUN uv sync --frozen --group dev --group test

COPY . .

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
