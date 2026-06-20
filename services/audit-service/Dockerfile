FROM python:3.12-slim

WORKDIR /app

COPY packages/py-shared/ ./packages/py-shared/
COPY services/audit-service/pyproject.toml ./
RUN pip install --no-cache-dir uv && \
    python3 -c "t=open('pyproject.toml').read();t=t.replace('gxp-shared = { workspace = true }','gxp-shared = { path = \"./packages/py-shared\", editable = true }');open('pyproject.toml','w').write(t)" && \
    uv pip install --system -e .

COPY services/audit-service/alembic.ini ./
COPY services/audit-service/app/ ./app/
COPY services/audit-service/worker/ ./worker/

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
