# --- AgenticLoopQA container image -----------------------------------------
# Small, single-stage image. The project has exactly one third-party
# dependency (the anthropic SDK), so multi-stage build isn't warranted.

FROM python:3.11-slim

# Keep Python from writing .pyc files / buffering stdout — nicer container logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest

# Copy the rest of the project.
COPY agentic_loop_qa/ ./agentic_loop_qa/
COPY tests/ ./tests/
COPY README.md .

# Run as a non-root user. Pre-create /app/reports (used as a volume mount
# target for `eval --out`) so it's writable by that user even when a host
# directory with different ownership is mounted over it.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/reports \
    && chown -R appuser:appuser /app
USER appuser

# No API key is baked into the image — pass ANTHROPIC_API_KEY at `docker run`
# time (or via --env-file) for live mode; the container runs in mock mode
# with zero configuration otherwise.

ENTRYPOINT ["python", "-m", "agentic_loop_qa.cli"]
CMD ["eval"]
