FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*

COPY packages/py-shared/ ./packages/py-shared/
COPY services/document-service/pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    python3 -c "t=open('pyproject.toml').read();t=t.replace('gxp-shared = { workspace = true }','gxp-shared = { path = \"./packages/py-shared\", editable = true }');open('pyproject.toml','w').write(t)" && \
    uv pip install --system -e .

COPY services/document-service/alembic.ini ./
COPY services/document-service/app/ ./app/

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
