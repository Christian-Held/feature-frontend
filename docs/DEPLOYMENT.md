# Deployment Guide

Comprehensive guide for deploying the Feature Auth Platform to production.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Application Deployment](#application-deployment)
5. [Database Migrations](#database-migrations)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [Rollback Procedures](#rollback-procedures)
9. [Scaling](#scaling)

---

## Prerequisites

### Required Services

- **PostgreSQL 15+** - Main database
- **Redis 7+** - Caching, rate limiting, Celery broker
- **SMTP Provider** - Email delivery (AWS SES, SendGrid, etc.)
- **Cloudflare Account** - Turnstile CAPTCHA
- **Object Storage** (Optional) - S3-compatible for backups/audit exports

### Required Tools

- Python 3.12+
- Node.js 20+
- Docker (optional, recommended)
- `uv` or `pip` for Python dependencies
- `npm` for frontend dependencies

###Required Access

- Domain with DNS control
- TLS certificates (Let's Encrypt recommended)
- Secrets management system

---

## Quick Start

### 1. Configuration

```bash
# Copy and configure environment
cp .env.example .env

# Edit .env with production values
# See CONFIGURATION.md for detailed guide
nano .env
```

### 2. Database Setup

```bash
# Create database
createdb feature_auth_prod

# Run migrations
alembic upgrade head

# Verify admin user created
psql feature_auth_prod -c "SELECT email, status FROM users WHERE email = 'admin@yourcompany.com';"
```

### 3. Backend Deployment

**Option A: Direct (systemd)**

```bash
# Install dependencies
uv pip install -r requirements.txt

# Run backend
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Option B: Docker**

```bash
# Build image
docker build -t feature-auth-api:latest -f Dockerfile.backend .

# Run container
docker run -d \
  --name auth-api \
  --env-file .env \
  -p 8000:8000 \
  feature-auth-api:latest
```

### 4. Celery Workers

```bash
# Start worker
celery -A backend.auth.email.celery_app worker --loglevel=info --concurrency=4

# Start beat (for scheduled tasks)
celery -A backend.auth.email.celery_app beat --loglevel=info
```

### 5. Frontend Deployment

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Serve static files (use nginx, caddy, or CDN)
# Output is in: frontend/dist/
```

### 6. Reverse Proxy Setup

See [Reverse Proxy Configuration](#reverse-proxy-configuration) below.

---

## Infrastructure Setup

### PostgreSQL

**Recommended Configuration:**

```ini
# postgresql.conf
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4
max_parallel_maintenance_workers = 2
```

**Backup Configuration:**

```bash
# Enable PITR
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'
wal_level = replica

# Daily full backups
0 2 * * * pg_basebackup -D /backup/$(date +\%Y\%m\%d) -Fp -Xs -P
```

**Connection Pooling (PgBouncer):**

```ini
# pgbouncer.ini
[databases]
feature_auth = host=localhost port=5432 dbname=feature_auth_prod

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
pool_mode = transaction
max_client_conn = 100
default_pool_size = 25
```

### Redis

**Recommended Configuration:**

```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

**Separate Instances (Recommended):**

- Redis Instance 1 (Port 6379): Celery broker + general cache
- Redis Instance 2 (Port 6380): Rate limiting (optional, for isolation)

### SMTP / Email Service

**AWS SES Setup:**

```bash
# Create SMTP credentials in AWS IAM
# Verify sender domain/email

# Test SMTP connection
python -c "
import smtplib
smtp = smtplib.SMTP('email-smtp.us-east-1.amazonaws.com', 587)
smtp.starttls()
smtp.login('SMTP_USER', 'SMTP_PASS')
print('SMTP OK')
smtp.quit()
"
```

**SendGrid Setup:**

```bash
# Create API key with Mail Send permissions
# Verify sender identity

# Test
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## Application Deployment

### Systemd Services

**1. FastAPI Application**

File: `/etc/systemd/system/feature-auth-api.service`

```ini
[Unit]
Description=Feature Auth API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/feature-auth
Environment="PATH=/opt/feature-auth/.venv/bin"
EnvironmentFile=/opt/feature-auth/.env
ExecStart=/opt/feature-auth/.venv/bin/uvicorn backend.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-config logging.yaml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**2. Celery Worker**

File: `/etc/systemd/system/feature-auth-celery.service`

```ini
[Unit]
Description=Feature Auth Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/feature-auth
Environment="PATH=/opt/feature-auth/.venv/bin"
EnvironmentFile=/opt/feature-auth/.env
ExecStart=/opt/feature-auth/.venv/bin/celery -A backend.auth.email.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=1000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. Celery Beat**

File: `/etc/systemd/system/feature-auth-celery-beat.service`

```ini
[Unit]
Description=Feature Auth Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/feature-auth
Environment="PATH=/opt/feature-auth/.venv/bin"
EnvironmentFile=/opt/feature-auth/.env
ExecStart=/opt/feature-auth/.venv/bin/celery -A backend.auth.email.celery_app beat \
    --loglevel=info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and Start:**

```bash
systemctl daemon-reload
systemctl enable feature-auth-api feature-auth-celery feature-auth-celery-beat
systemctl start feature-auth-api feature-auth-celery feature-auth-celery-beat

# Check status
systemctl status feature-auth-api
journalctl -u feature-auth-api -f
```

### Docker Compose

File: `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: feature_auth
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    command: >
      uvicorn backend.app:app
      --host 0.0.0.0
      --port 8000
      --workers 4
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    depends_on:
      - postgres
      - redis
    command: >
      celery -A backend.auth.email.celery_app worker
      --loglevel=info
      --concurrency=4
    restart: unless-stopped

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    env_file: .env
    depends_on:
      - redis
    command: >
      celery -A backend.auth.email.celery_app beat
      --loglevel=info
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**Deploy:**

```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
```

### Reverse Proxy Configuration

**Nginx:**

File: `/etc/nginx/sites-available/feature-auth`

```nginx
# Backend API
upstream api_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Force HTTPS
server {
    listen 80;
    server_name api.yourcompany.com;
    return 301 https://$server_name$request_uri;
}

# API Server
server {
    listen 443 ssl http2;
    server_name api.yourcompany.com;

    # TLS Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourcompany.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check (no rate limit)
    location /health {
        proxy_pass http://api_backend;
        access_log off;
    }
}

# Frontend
server {
    listen 443 ssl http2;
    server_name app.yourcompany.com;

    ssl_certificate /etc/letsencrypt/live/app.yourcompany.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.yourcompany.com/privkey.pem;

    root /var/www/feature-auth-frontend/dist;
    index index.html;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # CSP
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; connect-src 'self' https://api.cloudflare.com https://api.yourcompany.com; frame-src https://challenges.cloudflare.com; img-src 'self' data:;" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Caddy (Alternative):**

File: `Caddyfile`

```caddy
api.yourcompany.com {
    reverse_proxy localhost:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }

    @health path /health
    handle @health {
        reverse_proxy localhost:8000
        log {
            output discard
        }
    }
}

app.yourcompany.com {
    root * /var/www/feature-auth-frontend/dist
    encode gzip
    file_server
    try_files {path} /index.html

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        Content-Security-Policy "default-src 'self'; script-src 'self' https://challenges.cloudflare.com; connect-src 'self' https://api.yourcompany.com; frame-src https://challenges.cloudflare.com; img-src 'self' data:;"
    }
}
```

---

## Database Migrations

### Initial Setup

```bash
# Run all migrations
alembic upgrade head

# Verify current version
alembic current

# View migration history
alembic history --verbose
```

### Rolling Updates

```bash
# Before deploying new code
# 1. Backup database
pg_dump feature_auth_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Run new migrations
alembic upgrade head

# 3. Deploy new application code
systemctl restart feature-auth-api

# 4. Verify
curl https://api.yourcompany.com/health
```

### Rollback Migration

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Restore from backup (if needed)
psql feature_auth_prod < backup_20250107_120000.sql
```

---

## Post-Deployment Verification

### Health Checks

```bash
# API health
curl https://api.yourcompany.com/health
# Expected: {"status": "ok"}

# Database connectivity
curl https://api.yourcompany.com/v1/admin/users?page=1&page_size=1 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# Redis connectivity (check logs)
journalctl -u feature-auth-api | grep -i redis

# Celery workers
celery -A backend.auth.email.celery_app inspect active
```

### Functional Tests

```bash
# 1. Registration
curl -X POST https://api.yourcompany.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123",
    "captchaToken": "DUMMY_TOKEN_FOR_TEST"
  }'

# 2. Check email delivery
# Verify email received in test inbox

# 3. Login
curl -X POST https://api.yourcompany.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123"
  }'
```

### Performance Baseline

```bash
# Load test with Apache Bench
ab -n 1000 -c 10 -H "Authorization: Bearer TOKEN" \
  https://api.yourcompany.com/v1/auth/me

# Expected: p95 < 150ms for authenticated requests
```

---

## Monitoring & Alerts

### Prometheus Metrics

**Scrape Configuration:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'feature-auth-api'
    static_configs:
      - targets: ['api.yourcompany.com:8000']
    metrics_path: '/metrics'
```

**Key Metrics to Monitor:**

- `login_success_total` / `login_failure_total`
- `totp_failure_total`
- `refresh_success_total`
- `rate_limit_block_total`
- `email_enqueued_total`
- `http_request_duration_seconds` (p50, p95, p99)

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: auth_alerts
    interval: 30s
    rules:
      - alert: HighAuthFailureRate
        expr: rate(login_failure_total[5m]) > 10
        for: 2m
        annotations:
          summary: "High authentication failure rate"

      - alert: EmailQueueBacklog
        expr: celery_queue_length{queue="email"} > 100
        for: 5m
        annotations:
          summary: "Email queue backlog detected"

      - alert: APIHighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 0.5
        for: 5m
        annotations:
          summary: "API p95 latency > 500ms"
```

### Log Aggregation

**Recommended Stack:** Grafana Loki / ELK / Datadog

```bash
# Ship logs to centralized system
# Using Vector.dev example:

[sources.api_logs]
type = "file"
include = ["/var/log/feature-auth/api.log"]

[sinks.loki]
type = "loki"
inputs = ["api_logs"]
endpoint = "https://loki.yourcompany.com"
```

---

## Rollback Procedures

### Application Rollback

```bash
# 1. Stop services
systemctl stop feature-auth-api feature-auth-celery

# 2. Revert code
cd /opt/feature-auth
git checkout <previous-commit>
source .venv/bin/activate
uv pip install -r requirements.txt

# 3. Rollback database (if needed)
alembic downgrade <previous-revision>

# 4. Restart services
systemctl start feature-auth-api feature-auth-celery

# 5. Verify
curl https://api.yourcompany.com/health
```

### Database Rollback

```bash
# Full restore from backup
systemctl stop feature-auth-api
psql feature_auth_prod < backup_YYYYMMDD_HHMMSS.sql
systemctl start feature-auth-api
```

---

## Scaling

### Horizontal Scaling

**1. API Servers (Stateless)**

```bash
# Run multiple API instances behind load balancer
# Instance 1
uvicorn backend.app:app --port 8001 --workers 4

# Instance 2
uvicorn backend.app:app --port 8002 --workers 4

# Load balancer distributes traffic
```

**2. Celery Workers**

```bash
# Add more workers on separate machines
celery -A backend.auth.email.celery_app worker --loglevel=info --concurrency=8
```

### Vertical Scaling

**Database:**

- Increase `shared_buffers`, `effective_cache_size`
- Add read replicas for analytics queries
- Use connection pooling (PgBouncer)

**Redis:**

- Increase `maxmemory`
- Use Redis Cluster for HA

**API Servers:**

- Increase worker count: `--workers <CPU_CORES * 2>`
- Increase Uvicorn timeout settings

---

## SLO Targets (Per Spec)

- **Auth API p95 Latency:** < 150 ms
- **Login Error Rate:** < 1%
- **Email Delivery Start:** < 30s p95
- **RTO:** 1 hour
- **RPO:** 15 minutes

---

## Support & Troubleshooting

See `docs/TROUBLESHOOTING.md` for common issues and solutions.

For production incidents:
1. Check `journalctl -u feature-auth-api -n 100`
2. Check Prometheus metrics dashboard
3. Review audit logs: `/v1/admin/audit-logs`
4. Escalate to on-call engineer if not resolved in 15 minutes
