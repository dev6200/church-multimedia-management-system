FROM python:3.12-slim AS base
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS deps
COPY requirements.txt ./
RUN pip install -r requirements.txt

FROM deps AS dev
EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--reload"]

FROM deps AS prod
ENV PORT=8000 \
    WEB_CONCURRENCY=2
EXPOSE 8000
CMD ["sh","-c","gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY}"]

