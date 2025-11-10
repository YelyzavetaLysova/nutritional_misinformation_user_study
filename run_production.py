#!/usr/bin/env python3
"""
Production runner with Gunicorn for better concurrent handling.
Use this for higher participant loads (50+ concurrent users).
"""

import multiprocessing
import os

# Calculate optimal worker count
workers = min(4, (multiprocessing.cpu_count() * 2) + 1)

# Gunicorn configuration
bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

print(f"Starting production server with {workers} workers")
print(f"Each worker can handle ~25-50 concurrent participants")
print(f"Total estimated capacity: {workers * 30} concurrent participants")

if __name__ == "__main__":
    # Run with Gunicorn for production
    os.system(f"gunicorn app.main:app --workers {workers} --worker-class {worker_class} --bind {bind} --timeout {timeout}")
