"""Locust load — Spec Phase 10A WebSocket + HTTP smoke.

Usage:
  pip install locust
  locust -f scripts/load/locustfile.py --host http://127.0.0.1:8000
"""

from __future__ import annotations

import json
from locust import HttpUser, task, between


class BmwApiUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def metrics(self):
        self.client.get("/metrics")

    @task(1)
    def login_fail_rate(self):
        # Should eventually 429 under sustained abuse (Phase 10C)
        self.client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
            name="/api/v1/auth/login",
        )
