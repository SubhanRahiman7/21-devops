# syntax=docker/dockerfile:1
# ---------- Stage 1: build dependencies into a virtualenv ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: small runtime image ----------
FROM python:3.12-slim AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION} \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DATA_DIR=/data PORT=8080

# run as an unprivileged user; /data holds the SQLite database (a volume in Kubernetes)
RUN useradd --system --uid 10001 --home /app appuser \
 && mkdir -p /app /data && chown -R appuser /app /data
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=appuser app ./app
COPY --chown=appuser wsgi.py .
USER appuser
EXPOSE 8080
VOLUME ["/data"]
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8080'))" || exit 1
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - wsgi:app"]
