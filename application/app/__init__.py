"""DevOps Task Tracker – a small Flask service used to demonstrate the full DevOps toolchain."""
import hmac
import logging

from flask import Flask, Response, jsonify, render_template, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import Config
from .metrics import TASKS, init_metrics
from .storage import TaskStore


def create_app(config_overrides=None):
    app = Flask(__name__)
    cfg = Config()
    app.config.from_object(cfg)
    if config_overrides:
        app.config.update(config_overrides)
    logging.basicConfig(level=app.config["LOG_LEVEL"], format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("tasktracker")
    store = TaskStore(app.config["DATA_DIR"].rstrip("/") + "/tasks.db")
    app.extensions["store"] = store
    init_metrics(app)
    TASKS.set(store.count())

    def authorized():
        token = app.config["API_TOKEN"]
        if not token:
            return False, (jsonify(error="API_TOKEN is not configured; write operations are disabled"), 503)
        supplied = request.headers.get("X-API-Token", "")
        if not hmac.compare_digest(supplied, token):
            return False, (jsonify(error="missing or invalid X-API-Token"), 401)
        return True, None

    @app.get("/")
    def index():
        return render_template(
            "index.html", env=app.config["APP_ENV"], version=app.config["APP_VERSION"], host=app.config["HOSTNAME"]
        )

    @app.get("/health")                      # liveness probe: the process is up
    def health():
        return jsonify(status="healthy")

    @app.get("/ready")                       # readiness probe: dependencies (database) work
    def ready():
        try:
            store.ping()
        except Exception as exc:             # pragma: no cover - defensive
            log.error("readiness check failed: %s", exc)
            return jsonify(status="not-ready", error=str(exc)), 503
        return jsonify(status="ready")

    @app.get("/api/info")
    def info():
        return jsonify(
            name="devops-task-tracker", version=app.config["APP_VERSION"],
            environment=app.config["APP_ENV"], pod=app.config["HOSTNAME"], log_level=app.config["LOG_LEVEL"],
        )

    @app.get("/api/tasks")
    def list_tasks():
        return jsonify(store.list())

    @app.post("/api/tasks")
    def create_task():
        ok, err = authorized()
        if not ok:
            return err
        body = request.get_json(silent=True) or {}
        title = (body.get("title") or "").strip()
        if not title:
            return jsonify(error="'title' is required"), 400
        task = store.create(title)
        TASKS.set(store.count())
        log.info("task created id=%s", task["id"])
        return jsonify(task), 201

    @app.put("/api/tasks/<int:task_id>")
    def update_task(task_id):
        ok, err = authorized()
        if not ok:
            return err
        body = request.get_json(silent=True) or {}
        task = store.update(task_id, body.get("title"), body.get("done"))
        return (jsonify(task), 200) if task else (jsonify(error="task not found"), 404)

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        ok, err = authorized()
        if not ok:
            return err
        if not store.delete(task_id):
            return jsonify(error="task not found"), 404
        TASKS.set(store.count())
        return "", 204

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="route not found"), 404

    return app
