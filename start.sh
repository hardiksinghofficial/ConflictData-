#!/usr/bin/env bash

# IMPORTANT:
# This script runs both the FastAPI web server and the background poller
# in a single container to stay within Render Free Tier single-service limits.
#
# Startup order matters:
#   1. Start uvicorn (web API) first so Render's health check can pass.
#   2. Wait a few seconds for uvicorn to bind.
#   3. Start the poller in background — any crash there won't affect the web server.

# Ensure Python resolves our packages correctly
export PYTHONPATH="/app:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

PORT="${PORT:-10000}"

echo "==> Starting ConflictIQ API on port ${PORT}..."
# Run uvicorn in background first
python -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" &
UVICORN_PID=$!

# Give uvicorn time to bind before Render fires the health check
echo "==> Waiting 5 seconds for web server to initialise..."
sleep 5

# Verify uvicorn is still running
if ! kill -0 "${UVICORN_PID}" 2>/dev/null; then
    echo "ERROR: uvicorn failed to start. Aborting."
    exit 1
fi

echo "==> Web server is up (PID ${UVICORN_PID}). Starting background poller..."
# Start poller in background; errors here should NOT kill the web server
python -m poller.scheduler &
POLLER_PID=$!

echo "==> All processes started. Monitoring web server (PID ${UVICORN_PID})..."

# Keep container alive by waiting on uvicorn (the primary process)
wait "${UVICORN_PID}"
echo "==> Web server exited. Shutting down poller..."
kill "${POLLER_PID}" 2>/dev/null || true
