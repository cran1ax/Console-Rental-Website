"""
Gunicorn configuration for Corner Console.

Usage:
    gunicorn config.wsgi:application -c gunicorn.conf.py

Environment variables you can override:
    WEB_CONCURRENCY  — number of workers  (default: cpu_count * 2 + 1)
    GUNICORN_BIND    — bind address        (default: 0.0.0.0:8000)
    GUNICORN_TIMEOUT — worker timeout      (default: 120)
"""

import multiprocessing
import os

# ─── Server Socket ──────────────────────────────────────────────
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# ─── Worker Processes ───────────────────────────────────────────
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = 4
worker_connections = 1000
max_requests = 1000             # Recycle workers after 1000 requests
max_requests_jitter = 50        # Stagger restarts to avoid thundering herd

# ─── Timeouts ───────────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
keepalive = 5

# ─── Preload ────────────────────────────────────────────────────
preload_app = True              # Load app before forking → saves memory via CoW

# ─── Logging ────────────────────────────────────────────────────
accesslog = "-"                 # stdout
errorlog = "-"                  # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'
)

# ─── Process Naming ─────────────────────────────────────────────
proc_name = "corner_console"

# ─── Security ───────────────────────────────────────────────────
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# ─── Server Hooks ───────────────────────────────────────────────
def on_starting(server):
    """Called just before the master process is initialized."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers.")


def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info("Worker received INT or QUIT signal.")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal (timeout)."""
    worker.log.info("Worker received SIGABRT (timeout).")
