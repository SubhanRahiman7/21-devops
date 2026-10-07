"""Tiny SQLite storage layer (the database file lives on a persistent volume in Kubernetes)."""
import os
import sqlite3
from contextlib import contextmanager


class TaskStore:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        with self._conn() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS tasks ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
                "done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row(r):
        return {"id": r["id"], "title": r["title"], "done": bool(r["done"]), "created_at": r["created_at"]}

    def list(self):
        with self._conn() as c:
            return [self._row(r) for r in c.execute("SELECT * FROM tasks ORDER BY id")]

    def get(self, task_id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self._row(r) if r else None

    def create(self, title):
        with self._conn() as c:
            cur = c.execute("INSERT INTO tasks (title) VALUES (?)", (title,))
            return self.get_with(c, cur.lastrowid)

    def update(self, task_id, title=None, done=None):
        with self._conn() as c:
            if c.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
                return None
            if title is not None:
                c.execute("UPDATE tasks SET title = ? WHERE id = ?", (title, task_id))
            if done is not None:
                c.execute("UPDATE tasks SET done = ? WHERE id = ?", (int(bool(done)), task_id))
            return self.get_with(c, task_id)

    def delete(self, task_id):
        with self._conn() as c:
            return c.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount > 0

    def count(self):
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    def ping(self):
        with self._conn() as c:
            c.execute("SELECT 1")
        return True

    def get_with(self, conn, task_id):
        r = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row(r) if r else None
