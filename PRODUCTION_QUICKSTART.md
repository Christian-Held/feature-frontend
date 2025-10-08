# Production Deployment Quick Start

**Estimated time:** 6-8 hours for full production setup

## Prerequisites
- Ubuntu/Debian server with sudo access
- Domain name pointing to your server
- Port 80 and 443 open

## Step-by-Step Guide

### 1. Install Dependencies (15 min)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12+
sudo apt install python3.12 python3.12-venv python3-pip -y

# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Install Redis
sudo apt install redis-server -y

# Install Node.js 20+
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Nginx
sudo apt install nginx -y

# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
```

### 2. Set Up Database (10 min)
```bash
# Create PostgreSQL database
sudo -u postgres psql <<EOF
CREATE DATABASE feature_frontend;
CREATE USER feature_user WITH ENCRYPTED PASSWORD 'ChangeMe123!Secure';
GRANT ALL PRIVILEGES ON DATABASE feature_frontend TO feature_user;
\q
EOF

# Configure Redis
sudo sed -i 's/# requirepass .*/requirepass YourRedisPassword123/' /etc/redis/redis.conf
sudo systemctl restart redis
```

### 3. Clone and Configure Backend (20 min)
```bash
# Clone repository
cd /opt
sudo git clone <your-repo-url> feature-frontend
sudo chown -R $USER:$USER feature-frontend
cd feature-frontend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate secrets
python scripts/generate_jwt_keys.py > /tmp/jwt_key.json
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > /tmp/encryption_key.txt

# Create production .env
cat > .env <<'EOF'
# Database
DATABASE_URL=postgresql://feature_user:ChangeMe123!Secure@localhost:5432/feature_frontend
DATABASE_ECHO=false

# Redis
REDIS_URL=redis://:YourRedisPassword123@localhost:6379/0
REDIS_RATE_LIMIT_PREFIX=rate_limit
RATE_LIMIT_DEFAULT_REQUESTS=60
RATE_LIMIT_DEFAULT_WINDOW_SECONDS=60

# JWT (paste output from generate_jwt_keys.py)
JWT_JWK_CURRENT='{"paste":"from","jwt":"key.json"}'
JWT_ACCESS_TTL_SECONDS=420
JWT_REFRESH_TTL_SECONDS=2592000
JWT_ISSUER=feature-auth
JWT_AUDIENCE=feature-auth-clients
JWT_PREVIOUS_GRACE_SECONDS=86400

# Password Hashing
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=4
ARGON2_HASH_LEN=32

# CAPTCHA (Get from https://dash.cloudflare.com/)
TURNSTILE_SECRET_KEY=0x4AAAAAAA_YOUR_PRODUCTION_SECRET
TURNSTILE_VERIFY_URL=https://challenges.cloudflare.com/turnstile/v0/siteverify

# SMTP (Example: SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=apikey
SMTP_PASS=SG.your_api_key_here
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Your Company

# Celery
CELERY_BROKER_URL=redis://:YourRedisPassword123@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:YourRedisPassword123@localhost:6379/1

# URLs
FRONTEND_BASE_URL=https://yourdomain.com
API_BASE_URL=https://yourdomain.com

# Admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=GenerateStrongPassword123!

# Secrets (paste from encryption_key.txt)
EMAIL_VERIFICATION_SECRET=generate_random_32_char_string
ENCRYPTION_KEYS={"v1":"paste_from_encryption_key_txt"}
ENCRYPTION_KEY_ACTIVE=v1

# Observability
OTEL_EXPORTER_OTLP_ENDPOINT=
OTEL_EXPORTER_OTLP_INSECURE=true
SERVICE_NAME=feature-auth
SERVICE_VERSION=1.0.0
SERVICE_REGION=us-east-1

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info
EOF

# Run migrations
alembic upgrade head
```

### 4. Configure Frontend (15 min)
```bash
cd /opt/feature-frontend/frontend

# Create production .env
cat > .env <<'EOF'
VITE_API_BASE_URL=https://yourdomain.com
VITE_TURNSTILE_SITE_KEY=0x4AAAAAAA_YOUR_PRODUCTION_SITE_KEY
EOF

# Install dependencies and build
npm install
npm run build

# Build output is in dist/
```

### 5. Set Up Systemd Services (10 min)
```bash
# Backend service
sudo tee /etc/systemd/system/feature-auth.service > /dev/null <<EOF
[Unit]
Description=Feature Auth Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/feature-frontend
Environment="PATH=/opt/feature-frontend/.venv/bin"
ExecStart=/opt/feature-frontend/.venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Celery worker service
sudo tee /etc/systemd/system/feature-auth-celery.service > /dev/null <<EOF
[Unit]
Description=Feature Auth Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/feature-frontend
Environment="PATH=/opt/feature-frontend/.venv/bin"
ExecStart=/opt/feature-frontend/.venv/bin/celery -A backend.auth.email.tasks worker --loglevel=info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Start services
sudo systemctl daemon-reload
sudo systemctl enable feature-auth feature-auth-celery
sudo systemctl start feature-auth feature-auth-celery

# Check status
sudo systemctl status feature-auth feature-auth-celery
```

### 6. Configure Nginx + SSL (20 min)
```bash
# Create Nginx config
sudo tee /etc/nginx/sites-available/feature-auth > /dev/null <<'EOF'
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL will be configured by certbot

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Backend API
    location /v1 {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    # Metrics (restrict to internal only)
    location /metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8000/metrics;
    }

    # Frontend static files
    location / {
        root /opt/feature-frontend/frontend/dist;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/feature-auth /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test config
sudo nginx -t

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com --non-interactive --agree-tos -m admin@yourdomain.com

# Reload Nginx
sudo systemctl reload nginx
```

### 7. Verify Deployment (10 min)
```bash
# Check services are running
sudo systemctl status feature-auth
sudo systemctl status feature-auth-celery
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Test health endpoint
curl https://yourdomain.com/health

# Test backend API
curl https://yourdomain.com/v1/auth/login

# Check logs if any issues
sudo journalctl -u feature-auth -f
sudo journalctl -u feature-auth-celery -f
```

### 8. Set Up Monitoring (30 min)
```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvf prometheus-*.tar.gz
sudo mv prometheus-*/prometheus /usr/local/bin/
sudo mv prometheus-*/promtool /usr/local/bin/

# Create Prometheus config
sudo mkdir -p /etc/prometheus
sudo tee /etc/prometheus/prometheus.yml > /dev/null <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'feature-auth'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
EOF

# Create Prometheus systemd service
sudo tee /etc/systemd/system/prometheus.service > /dev/null <<EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/var/lib/prometheus
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo mkdir -p /var/lib/prometheus
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### 9. Set Up Backups (15 min)
```bash
# Create backup directory
sudo mkdir -p /backups
sudo chown postgres:postgres /backups

# Create backup script
sudo tee /usr/local/bin/backup-postgres.sh > /dev/null <<'EOF'
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
pg_dump -U feature_user feature_frontend | gzip > /backups/feature-frontend-${TIMESTAMP}.sql.gz

# Keep only last 30 days
find /backups -name "feature-frontend-*.sql.gz" -mtime +30 -delete

# Log backup
echo "${TIMESTAMP}: Backup completed" >> /var/log/postgres-backup.log
EOF

sudo chmod +x /usr/local/bin/backup-postgres.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-postgres.sh" | sudo crontab -
```

### 10. Security Hardening (15 min)
```bash
# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Disable root SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Set up fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## Post-Deployment Checklist

- [ ] All services running (backend, celery, nginx, postgres, redis)
- [ ] SSL certificate installed and HTTPS working
- [ ] Can register a test user
- [ ] Verification email received
- [ ] Can log in with verified user
- [ ] 2FA setup works
- [ ] Admin account accessible
- [ ] Monitoring operational (Prometheus)
- [ ] Backups configured
- [ ] Firewall configured
- [ ] Rate limiting tested (try 10 failed logins)

## Troubleshooting

### Backend won't start
```bash
# Check logs
sudo journalctl -u feature-auth -n 100 --no-pager

# Common issues:
# - Database connection failed: Check DATABASE_URL in .env
# - Redis connection failed: Check REDIS_URL and redis service
# - Missing JWT keys: Run generate_jwt_keys.py
```

### Emails not sending
```bash
# Check Celery logs
sudo journalctl -u feature-auth-celery -n 100 --no-pager

# Test SMTP directly
python3 -c "import smtplib; smtplib.SMTP('your-smtp-host', 587).starttls()"
```

### Frontend shows 404 for API calls
```bash
# Check Nginx proxy
sudo nginx -t
sudo tail -f /var/log/nginx/error.log

# Verify backend is listening
curl http://localhost:8000/health
```

## Maintenance

### Update Application
```bash
cd /opt/feature-frontend
git pull
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd frontend && npm install && npm run build
sudo systemctl restart feature-auth feature-auth-celery
```

### View Logs
```bash
# Backend
sudo journalctl -u feature-auth -f

# Celery
sudo journalctl -u feature-auth-celery -f

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restore from Backup
```bash
# Stop services
sudo systemctl stop feature-auth feature-auth-celery

# Restore database
gunzip < /backups/feature-frontend-TIMESTAMP.sql.gz | psql -U feature_user feature_frontend

# Restart services
sudo systemctl start feature-auth feature-auth-celery
```

## Support Resources

- **Implementation Status:** `docs/IMPLEMENTATION_STATUS.md`
- **Configuration Guide:** `docs/CONFIGURATION.md`
- **Deployment Guide:** `docs/DEPLOYMENT.md`
- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **API Docs:** https://yourdomain.com/docs (when backend is running)

---

**Last Updated:** 2025-10-07
**Deployment Time:** 6-8 hours
**Difficulty:** Intermediate
