"""Prometheus metrics (exposed on /metrics)."""
import time

from flask import g, request
from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)
TASKS = Gauge("tasks_total", "Number of tasks stored")
INFO = Gauge("app_info", "Application info", ["version", "environment"])


def init_metrics(app):
    INFO.labels(version=app.config["APP_VERSION"], environment=app.config["APP_ENV"]).set(1)

    @app.before_request
    def _start():
        g._t0 = time.perf_counter()

    @app.after_request
    def _record(resp):
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        if endpoint != "/metrics":
            REQUESTS.labels(request.method, endpoint, resp.status_code).inc()
            LATENCY.labels(endpoint).observe(time.perf_counter() - getattr(g, "_t0", time.perf_counter()))
        return resp
