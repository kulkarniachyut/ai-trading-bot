# Step 20: Docker Deployment

**Status:** Planned
**Branch:** `feature/deploy-20-docker`

## Objective

Containerize the entire system for VPS deployment. Single Docker container running both India and US schedulers.

## Deliverables

### 1. Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

### 2. docker-compose.yaml
```yaml
version: '3.8'
services:
  trading-bot:
    build: .
    env_file: .env
    volumes:
      - ./db:/app/db
      - ./logs:/app/logs
    restart: unless-stopped
```

### 3. Root main.py
- Imports and runs both India and US main modules
- Handles graceful shutdown (SIGTERM, SIGINT)
- Health check endpoint (optional)

### 4. Deployment Scripts
- `scripts/deploy.sh` — build + push + restart
- `scripts/backup.sh` — DB backup to host
- `scripts/health_check.sh` — verify system running

## Resource Estimates

| Resource | Estimate |
|----------|----------|
| RAM idle | ~200MB |
| RAM peak | ~500MB |
| CPU | Low (bursty) |
| Disk | < 1GB |
| Network | ~200 API calls/day |

## Key Constraints

- `.env` file never included in Docker image
- DB and logs mounted as Docker volumes (persist across restarts)
- `restart: unless-stopped` for auto-recovery
- Docker health check monitors process + last successful job

## Files to Create

| File | Description |
|------|-------------|
| `Dockerfile` | Container definition |
| `docker-compose.yaml` | Service orchestration |
| `main.py` | Root entry point (both systems) |
| `.dockerignore` | Exclude .env, .git, tests, etc. |
| `scripts/deploy.sh` | Deployment script |
| `scripts/backup.sh` | DB backup script |

## Testing

- Build image, run container with test env
- Verify both schedulers start
- Verify DB volumes persist across container restart
- Verify graceful shutdown (SIGTERM)
