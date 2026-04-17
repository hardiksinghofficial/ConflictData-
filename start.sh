#!/usr/bin/env bash

# ConflictIQ startup script — runs both FastAPI and the background poller
# in a single container (fits within Koyeb's free web service quota).
#
# Startup order:
#   1. Start uvicorn first so Koyeb's health check passes quickly.
#   2. Wait 5 seconds for uvicorn to fully bind.
#   3. Start the poller in the background — a poller crash won't kill the API.

# Ensure Python resolves our packages correctly
export PYTHONPATH="/app:${PYTHONPATH}"
export PYTHONUNBUFFERED=1

PORT="${PORT:-7860}"

echo "==> Starting ConflictIQ API on port ${PORT}..."
python -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}" &
UVICORN_PID=$!

echo "==> Waiting 5 seconds for web server to initialise..."
sleep 5

# Verify uvicorn is still alive
if ! kill -0 "${UVICORN_PID}" 2>/dev/null; then
    echo "ERROR: uvicorn failed to start. Aborting."
    exit 1
fi

echo "==> Web server is up (PID ${UVICORN_PID}). Starting background poller..."
python -m poller.scheduler &
POLLER_PID=$!

echo "==> All processes running. Container will exit when web server stops."

# Keep container alive — wait on uvicorn (primary process)
wait "${UVICORN_PID}"
echo "==> Web server exited. Shutting down poller..."
kill "${POLLER_PID}" 2>/dev/null || true
