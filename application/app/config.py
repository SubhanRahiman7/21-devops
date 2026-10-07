"""Runtime configuration, read from environment variables.

In Kubernetes the non-sensitive values come from a ConfigMap and API_TOKEN from a Secret.
"""
import os
import socket


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    APP_VERSION = os.getenv("APP_VERSION", "dev")
    DATA_DIR = os.getenv("DATA_DIR", "./data")
    API_TOKEN = os.getenv("API_TOKEN", "")          # empty -> write endpoints are disabled (503)
    HOSTNAME = os.getenv("HOSTNAME", socket.gethostname())

    @property
    def db_path(self):
        return os.path.join(self.DATA_DIR, "tasks.db")
