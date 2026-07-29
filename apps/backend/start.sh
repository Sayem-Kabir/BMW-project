#!/bin/sh
# Render / Docker entrypoint — Module 7F
set -e
PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
