#!/usr/bin/env bash

# IMPORTANT:
# This script is required to bypass Render's Free Tier web worker limits.
# Render only gives enough hours to run a single service 24/7.
# By starting both processes in the same container, we share that quota securely.

# Start the background poller in the background
echo "Starting background ingestion poller..."
python -m poller.scheduler &

# Start the FastAPI web server in the foreground
# Render relies on binding to the exact PORT environment variable they pass
echo "Starting FastAPI web instance on port ${PORT:-10000}..."
python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-10000}
