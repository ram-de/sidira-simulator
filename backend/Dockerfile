FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN addgroup --system sidira && adduser --system --ingroup sidira sidira

COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY sidira_simulator ./sidira_simulator

RUN pip install --upgrade pip && pip install .

USER sidira

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["sh", "-c", "uvicorn sidira_simulator.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
