"""Gunicorn configuration for production.

Tunables come from the environment so the same image works across hosts:
- WEB_CONCURRENCY  number of worker processes (default: 2*cores + 1)
- GUNICORN_BIND    address:port to bind (default: 0.0.0.0:8000)
- GUNICORN_TIMEOUT worker timeout in seconds (default: 60)
"""

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))

# Recycle workers periodically to bound memory growth.
max_requests = 1000
max_requests_jitter = 100

# Log to stdout/stderr so the platform collects them.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
