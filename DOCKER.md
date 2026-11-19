# CriticRAG AI — Docker & Containerization Reference

> Complete technical guide for building, running, configuring, and deploying CriticRAG AI inside Docker containers and Docker Compose environments.

---

## 1. Containerization Architecture Overview

CriticRAG AI is fully containerized to run seamlessly across any environment (development, CI/CD, production) without requiring a local Python setup.

### Key Architectural Principles
- **Base Image**: `python:3.11-slim` (Lightweight Debian-based Python footprint).
- **Single-Stage Build**: Keeps the image minimal as the project relies on lightweight dependencies (`anthropic`, `pytest`).
- **Security & Non-Root Execution**: Runs as non-root user `appuser` (UID 1000) to prevent privilege escalation vulnerabilities.
- **Zero Secrets Baked In**: API keys are never compiled into the container layer; they are injected at runtime via environment variables or `.env` files.
- **Pre-Created Mount Permissions**: `/app/reports` is pre-created and chowned to `appuser:appuser` to ensure writable volume mounts.

---

## 2. Dockerfile Specification (`Dockerfile`)

```dockerfile
# Base Image: Python 3.11 Slim
FROM python:3.11-slim

# Prevent Python bytecode creation & unbuffer logs for immediate terminal output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pytest

# Copy application source code
COPY agentic_loop_qa/ ./agentic_loop_qa/
COPY tests/ ./tests/
COPY README.md .

# Create non-root security user & pre-create volume target directory
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/reports \
    && chown -R appuser:appuser /app

USER appuser

# Container Entrypoint & Default Command
ENTRYPOINT ["python", "-m", "agentic_loop_qa.cli"]
CMD ["eval"]
```

---

## 3. Environment Variables & Security Configurations

| Variable Name | Required? | Default in Container | Description |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Optional | Unset | Google Gemini API key (Free Tier). Enables **Live Mode** via Google Gemini API. |
| `ANTHROPIC_API_KEY` | Optional | Unset | Anthropic API key. Enables **Live Mode** via Anthropic Messages API. |
| `AGENTICLOOPQA_MOCK` | Optional | `0` (if key set) / `1` | Forces Mock Mode when set to `1`. |
| `AGENTICLOOPQA_MODEL` | Optional | `gemini-3.6-flash` | Model identifier (`gemini-3.6-flash`, `claude-sonnet-5`, etc.). |
| `AGENTICLOOPQA_MAX_ITERATIONS` | Optional | `3` | Iteration budget cap for the self-correction loop. |
| `AGENTICLOOPQA_CONF_THRESHOLD` | Optional | `0.85` | Confidence threshold for early termination. |

---

## 4. Docker CLI Execution Commands

### 1. Build the Image
```bash
docker build -t agentic-loop-qa .
```

### 2. Run Single Question Query (`ask`)

#### Mock Mode (Default - No API key required):
```bash
docker run --rm agentic-loop-qa ask "Who designed the Eiffel Tower?"
```

#### Live Mode (Google Gemini Free Tier):
```bash
docker run --rm -e GEMINI_API_KEY=AIzaSyA... agentic-loop-qa ask "Who designed the Eiffel Tower?"
```

#### Live Mode (Anthropic):
```bash
docker run --rm -e ANTHROPIC_API_KEY=sk-ant-api03-... agentic-loop-qa ask "Who designed the Eiffel Tower?"
```

#### Using Environment File:
```bash
docker run --rm --env-file .env agentic-loop-qa ask "Who painted the Mona Lisa?"
```

---

### 3. Run Benchmark Evaluation (`eval`)

Writes benchmark results to a mounted directory on your host machine:

```bash
# Create local reports directory
mkdir -p reports

# Run evaluation and save output to host
docker run --rm \
  -v $(pwd)/reports:/app/reports \
  --env-file .env \
  agentic-loop-qa eval --out /app/reports/report.json
```

---

### 4. Run Test Suite Inside Container

Override the default entrypoint to run `pytest`:

```bash
docker run --rm --entrypoint python agentic-loop-qa -m pytest -q
```

---

### 5. Interactive Debugging Shell

Launch a interactive bash shell inside the container:

```bash
docker run --rm -it --entrypoint /bin/bash agentic-loop-qa
```

---

## 5. Docker Compose Services (`docker-compose.yml`)

The project includes a `docker-compose.yml` defining predefined services for evaluation and testing.

```yaml
version: "3.9"

services:
  # Main application service (Default action: eval)
  agentic-loop-qa:
    build: .
    image: agentic-loop-qa:latest
    env_file:
      - path: .env
        required: false
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
    volumes:
      - ./reports:/app/reports
    command: ["eval", "--out", "/app/reports/report.json"]

  # Automated Test Suite service
  test:
    build: .
    image: agentic-loop-qa:latest
    entrypoint: ["python", "-m", "pytest", "-q"]
    command: []
```

### Docker Compose Usage Commands

```bash
# Run default evaluation service
docker compose run --rm agentic-loop-qa

# Run single question ask query via Compose
docker compose run --rm agentic-loop-qa ask "Who discovered penicillin?"

# Run unit tests via Compose
docker compose run --rm test
```

---

## 6. Makefile Shortcuts

A `Makefile` simplifies common Docker commands:

```makefile
.PHONY: build ask eval test shell clean

IMAGE := agentic-loop-qa:latest

build:
	docker build -t $(IMAGE) .

ask:
	docker run --rm --env-file .env $(IMAGE) ask "$(Q)"

eval:
	mkdir -p reports
	docker run --rm --env-file .env -v $$(pwd)/reports:/app/reports $(IMAGE) eval --out /app/reports/report.json

test:
	docker run --rm --entrypoint python $(IMAGE) -m pytest -q

shell:
	docker run --rm -it --env-file .env --entrypoint /bin/bash $(IMAGE)

clean:
	docker rmi $(IMAGE) 2>/dev/null || true
```

### Command Usage Matrix

| Command | Action | Example |
| :--- | :--- | :--- |
| `make build` | Builds Docker image `agentic-loop-qa:latest` | `make build` |
| `make ask` | Runs single question query with environment variables | `make ask Q="Who painted the Mona Lisa?"` |
| `make eval` | Runs evaluation and writes host report `./reports/report.json` | `make eval` |
| `make test` | Executes `pytest` unit test suite inside container | `make test` |
| `make shell` | Drops into interactive bash shell inside container | `make shell` |
| `make clean` | Removes container image | `make clean` |

---

## 7. Troubleshooting & Permission Handling

### Volume Mount Permission Error on Linux Hosts
If you mount `./reports` on a Linux host with a different user ID, file write permission errors may occur when `appuser` (UID 1000) writes to `/app/reports`.

**Quick Fix on Host**:
```bash
chmod 777 reports
```

**Recommended Host Fix**:
```bash
chown -R 1000:1000 reports
```

---

## Related Documentation Files

- [PROJECT_OVERVIEW.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/PROJECT_OVERVIEW.md) — High-level project architecture and setup.
- [BACKEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/BACKEND.md) — Engine components, agents, and evaluation framework.
- [FRONTEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/FRONTEND.md) — CLI output specs and Web Dashboard design specs.
- [APIS.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/APIS.md) — Python, CLI, REST, and WebSocket API specifications.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — Relational & Vector SQL schemas for all system components.
