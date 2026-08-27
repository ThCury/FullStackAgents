FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/agents ./agents
COPY backend/application ./application
COPY backend/domain ./domain
COPY backend/infrastructure ./infrastructure
COPY backend/pipeline ./pipeline
COPY backend/routes ./routes
COPY backend/config.py backend/container.py backend/main.py ./
COPY template /template

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
