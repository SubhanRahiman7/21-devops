"""DevOps Task Tracker – a small Flask service used to demonstrate the full DevOps toolchain."""
import hmac
import logging

from flask import Flask, Response, jsonify, render_template_string, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import Config
from .metrics import TASKS, init_metrics
from .storage import TaskStore

INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevOps Task Tracker</title>
<style>
 :root{--bg:#0f172a;--card:#1e293b;--fg:#e2e8f0;--mut:#94a3b8;--acc:#38bdf8;--ok:#4ade80}
 *{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
 main{max-width:860px;margin:0 auto;padding:32px 20px}h1{margin:0 0 4px;font-size:28px}
 .sub{color:var(--mut);margin-bottom:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:24px}
 .card{background:var(--card);border-radius:12px;padding:14px 16px}.k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
 .v{font-size:18px;margin-top:4px;word-break:break-all}.ok{color:var(--ok)}
 ul{list-style:none;padding:0;margin:0}li{background:var(--card);border-radius:10px;padding:12px 16px;margin-bottom:8px;display:flex;justify-content:space-between}
 .done{text-decoration:line-through;color:var(--mut)}.pill{color:var(--acc);font-size:12px}
</style></head><body><main>
<h1>DevOps Task Tracker</h1><div class="sub">Application → Git → CI/CD → Docker → Kubernetes → Helm → Monitoring → GitOps</div>
<div class="grid">
 <div class="card"><div class="k">Environment</div><div class="v">{{ env }}</div></div>
 <div class="card"><div class="k">Version</div><div class="v">{{ version }}</div></div>
 <div class="card"><div class="k">Served by (pod)</div><div class="v">{{ host }}</div></div>
 <div class="card"><div class="k">Health</div><div class="v ok" id="health">checking…</div></div>
</div>
<h2>Tasks <span class="pill" id="count"></span></h2><ul id="tasks"></ul>
<script>
fetch('/health').then(r=>r.json()).then(d=>{document.getElementById('health').textContent=d.status.toUpperCase()});
fetch('/api/tasks').then(r=>r.json()).then(d=>{document.getElementById('count').textContent=d.length+' total';
 document.getElementById('tasks').innerHTML=d.map(t=>'<li><span class="'+(t.done?'done':'')+'">'+t.title+'</span><span class="pill">'+(t.done?'done':'open')+'</span></li>').join('')||'<li>No tasks yet</li>'});
</script></main></body></html>"""


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
        return render_template_string(
            INDEX_HTML, env=app.config["APP_ENV"], version=app.config["APP_VERSION"], host=app.config["HOSTNAME"]
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
