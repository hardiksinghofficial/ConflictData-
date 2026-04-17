# ============================================================
# Dockerfile — Hugging Face Spaces deployment
# HF Spaces requires:
#   - App listening on port 7860
#   - Container runs as non-root (UID 1000)
# ============================================================
FROM python:3.11-slim

# dos2unix: fixes Windows CRLF in start.sh (edited on Windows, run on Linux)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# HF Spaces injects secrets as env vars; PORT is fixed at 7860
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=7860

# Install Python dependencies (cached layer — only rebuilds if requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy English model via direct GitHub release URL
RUN pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

# Copy full application codebase
COPY . .

# Fix Windows CRLF -> LF and set executable bit
RUN dos2unix start.sh && chmod +x start.sh

# Give ownership to UID 1000 (HF Spaces non-root requirement)
RUN chown -R 1000:1000 /app

# Switch to non-root user
USER 1000

EXPOSE 7860

CMD ["/bin/bash", "start.sh"]

