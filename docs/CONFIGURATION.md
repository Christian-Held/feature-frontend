# Configuration Guide

This document lists all configuration points that need to be changed from dummy/development values to production values.

## 🔧 Required Environment Variables

### Database Configuration
**File:** `.env`

```bash
# Change from SQLite to PostgreSQL for production
DATABASE_URL=postgresql://user:password@localhost:5432/feature_auth
# Example production:
# DATABASE_URL=postgresql://prod_user:STRONG_PASSWORD@prod-db.example.com:5432/feature_auth_prod

DATABASE_ECHO=false  # Set to false in production
```

### Redis Configuration
**File:** `.env`

```bash
# Development
REDIS_URL=redis://localhost:6379/0

# Production
REDIS_URL=redis://prod-redis.example.com:6379/0
# Or with password:
# REDIS_URL=redis://:REDIS_PASSWORD@prod-redis.example.com:6379/0
```

### JWT Configuration
**File:** `.env`

⚠️ **CRITICAL**: Generate new ES256 keys for production!

```bash
# Generate keys using:
# python -c "from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.backends import default_backend; from cryptography.hazmat.primitives import serialization; key = ec.generate_private_key(ec.SECP256R1(), default_backend()); print(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()).decode())"

JWT_JWK_CURRENT='{"kty":"EC","crv":"P-256","x":"...","y":"...","d":"...","kid":"2025-01"}'
JWT_JWK_NEXT=null
JWT_JWK_PREVIOUS=null

JWT_ACCESS_TTL_SECONDS=420  # 7 minutes
JWT_REFRESH_TTL_SECONDS=2592000  # 30 days
JWT_ISSUER=feature-auth
JWT_AUDIENCE=feature-auth-clients
```

### Argon2 Password Hashing
**File:** `.env`

```bash
# Production-recommended values (per spec)
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536  # 64 MB
ARGON2_PARALLELISM=2
ARGON2_HASH_LEN=32
```

### Cloudflare Turnstile CAPTCHA
**File:** `.env`

⚠️ **MUST CHANGE**: Replace with your Cloudflare Turnstile credentials

```bash
# Development (dummy key)
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA

# Production - Get from: https://dash.cloudflare.com/
TURNSTILE_SECRET_KEY=0x4AAAAAAAA...YOUR_SECRET_KEY
TURNSTILE_SITE_KEY=0x4AAAAAAAA...YOUR_SITE_KEY  # For frontend

TURNSTILE_VERIFY_URL=https://challenges.cloudflare.com/turnstile/v0/siteverify
```

**Frontend Configuration:**
**File:** `frontend/src/config/turnstile.ts` (create this file)

```typescript
export const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || '1x00000000000000000000AA'
```

### Email/SMTP Configuration
**File:** `.env`

⚠️ **MUST CHANGE**: Replace with production SMTP credentials

```bash
# Development (dummy SMTP - emails won't send)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USE_TLS=false
EMAIL_FROM_ADDRESS=noreply@localhost
EMAIL_FROM_NAME=Feature Auth Dev

# Production Examples:

# Option 1: AWS SES
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=AKIAIOSFODNN7EXAMPLE
SMTP_PASS=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
EMAIL_FROM_ADDRESS=noreply@yourcompany.com
EMAIL_FROM_NAME=YourCompany Auth

# Option 2: SendGrid
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=apikey
SMTP_PASS=SG.YOUR_SENDGRID_API_KEY
EMAIL_FROM_ADDRESS=noreply@yourcompany.com
EMAIL_FROM_NAME=YourCompany

# Option 3: Custom SMTP
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your-smtp-user
SMTP_PASS=your-smtp-password
EMAIL_FROM_ADDRESS=noreply@yourcompany.com
EMAIL_FROM_NAME=YourCompany
```

### Celery Configuration
**File:** `.env`

```bash
# Use Redis as broker
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Production
CELERY_BROKER_URL=redis://prod-redis.example.com:6379/1
CELERY_RESULT_BACKEND=redis://prod-redis.example.com:6379/1
```

### Admin Account
**File:** `.env`

⚠️ **MUST CHANGE**: Create secure admin credentials

```bash
# Development
ADMIN_EMAIL=admin@localhost
ADMIN_PASSWORD=admin123

# Production
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=VERY_STRONG_PASSWORD_MIN_12_CHARS
```

### Encryption Keys
**File:** `.env`

⚠️ **CRITICAL**: Generate new keys for production!

```bash
# Generate using:
# python -c "import secrets; import base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

ENCRYPTION_KEYS='{"v1":"REPLACE_WITH_32_BYTE_BASE64_KEY"}'
ENCRYPTION_KEY_ACTIVE=v1

# Example:
# ENCRYPTION_KEYS='{"v1":"7x9Kj3mN8qR5tY2wE4uI1oP6aS0dF-gH_zX5cV7bN9M="}'
```

### Frontend URLs
**File:** `.env`

```bash
# Development
FRONTEND_BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000

# Production
FRONTEND_BASE_URL=https://app.yourcompany.com
API_BASE_URL=https://api.yourcompany.com
```

**Frontend File:** `frontend/.env` or `frontend/.env.production`

```bash
# Development
VITE_API_BASE_URL=http://localhost:8000
VITE_TURNSTILE_SITE_KEY=1x00000000000000000000AA

# Production
VITE_API_BASE_URL=https://api.yourcompany.com
VITE_TURNSTILE_SITE_KEY=0x4AAAAAAAA...YOUR_SITE_KEY
```

### Email Verification Secret
**File:** `.env`

⚠️ **MUST CHANGE**: Generate random secret

```bash
# Generate using:
# python -c "import secrets; print(secrets.token_urlsafe(32))"

EMAIL_VERIFICATION_SECRET=REPLACE_WITH_RANDOM_32_BYTE_SECRET
```

### Observability (OpenTelemetry)
**File:** `.env`

```bash
# Optional - for production monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_EXPORTER_OTLP_INSECURE=true

# Production with collector
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel-collector.yourcompany.com:4318
OTEL_EXPORTER_OTLP_INSECURE=false

SERVICE_NAME=auth
SERVICE_VERSION=0.1.0
SERVICE_REGION=us-east-1
```

### Rate Limiting
**File:** `.env`

```bash
RATE_LIMIT_DEFAULT_REQUESTS=60
RATE_LIMIT_DEFAULT_WINDOW_SECONDS=60
RATE_LIMIT_ALLOWLIST=  # Comma-separated IPs to allow
RATE_LIMIT_DENYLIST=  # Comma-separated IPs to block
```

### Logging
**File:** `.env`

```bash
LOG_LEVEL=INFO  # Use INFO or WARNING in production
LOG_REDACT_FIELDS=password,token,secret,captcha
```

---

## 📋 Configuration Checklist

Before deploying to production, verify:

- [ ] **PostgreSQL URL** configured (not SQLite)
- [ ] **Redis URL** points to production instance
- [ ] **JWT keys** regenerated (ES256 P-256)
- [ ] **Encryption keys** regenerated (32-byte)
- [ ] **Admin password** is strong (min 12 chars)
- [ ] **Turnstile keys** from Cloudflare dashboard
- [ ] **SMTP credentials** configured and tested
- [ ] **Email FROM address** uses your domain
- [ ] **Frontend/API URLs** point to production domains
- [ ] **Email verification secret** regenerated
- [ ] **DATABASE_ECHO** set to false
- [ ] **LOG_LEVEL** set to INFO or WARNING
- [ ] All secrets stored securely (not in git)

---

## 🔐 Secrets Management

### Recommended Approaches

1. **Environment Variables** (Cloud platforms)
   - AWS: Parameter Store or Secrets Manager
   - GCP: Secret Manager
   - Azure: Key Vault
   - Heroku: Config Vars

2. **Docker Secrets** (Docker Swarm/Kubernetes)
   ```yaml
   version: '3.8'
   services:
     api:
       image: feature-auth-api
       secrets:
         - database_url
         - jwt_jwk_current
   secrets:
     database_url:
       external: true
     jwt_jwk_current:
       external: true
   ```

3. **Kubernetes Secrets**
   ```yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: auth-secrets
   type: Opaque
   data:
     DATABASE_URL: <base64-encoded>
     JWT_JWK_CURRENT: <base64-encoded>
   ```

---

## 📧 Email Templates Customization

**Location:** `backend/auth/email/templates.py`

Update the following for your brand:

- Company name
- Logo URL
- Support email
- Brand colors (if HTML templates added)
- Legal footer text

---

## 🌐 CORS Configuration

**File:** `backend/app.py`

Update CORS origins for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.yourcompany.com",
        "https://www.yourcompany.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Next Steps

1. Copy `.env.example` to `.env`
2. Replace all dummy values with production values
3. Run configuration test: `python scripts/test_config.py`
4. See `DEPLOYMENT.md` for deployment instructions
