FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv

RUN uv sync --frozen

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

CMD ["uv", "run", "fastapi", "dev", "app/main.py", "--host", "0.0.0.0"]