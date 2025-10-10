# Feature Platform - Developer Documentation

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Authentication & Authorization System](#authentication--authorization-system)
5. [Database Schema](#database-schema)
6. [API Routes Reference](#api-routes-reference)
7. [Security & Rate Limiting](#security--rate-limiting)
8. [Email & Notifications](#email--notifications)
9. [Configuration Management](#configuration-management)
10. [Development Workflow](#development-workflow)
11. [Deployment & Operations](#deployment--operations)
12. [Testing Strategy](#testing-strategy)

---

## System Architecture Overview

### Dual Backend Architecture

The application uses a **dual backend architecture** with two separate FastAPI applications:

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React + Vite)                 │
│                    http://localhost:5173                     │
└───────────────┬─────────────────────────────┬───────────────┘
                │                             │
                │ Vite Proxy Routes           │
                │                             │
    ┌───────────▼──────────┐      ┌──────────▼──────────────┐
    │  Auth Backend        │      │  Main Dashboard App     │
    │  (backend/app.py)    │      │  (app/main.py)          │
    │  Port 8000           │      │  Port 3000              │
    │                      │      │                         │
    │  - /v1/auth/*        │      │  - /api/*               │
    │  - User registration │      │  - /jobs/*              │
    │  - Login/logout      │      │  - /tasks/*             │
    │  - 2FA management    │      │  - /health              │
    │  - Password reset    │      │  - /ws (WebSocket)      │
    │  - JWT tokens        │      │  - Job orchestration    │
    └──────────┬───────────┘      └──────────┬──────────────┘
               │                             │
               │                             │
    ┌──────────▼─────────────────────────────▼──────────────┐
    │              Shared Infrastructure                     │
    │  - PostgreSQL Database                                 │
    │  - Redis Cache & Rate Limiting                         │
    │  - Celery Task Queue                                   │
    │  - SMTP Email Service                                  │
    └────────────────────────────────────────────────────────┘
```

### Request Routing Strategy

The frontend uses **Vite proxy** to route requests to the appropriate backend:

- **Auth requests** (`/v1/*`) → Port 8000 (Auth Backend)
- **Dashboard requests** (`/api/*`, `/jobs/*`, `/tasks/*`, `/health`) → Port 3000 (Main App)
- **WebSocket** (`/ws`) → Port 3000 (Main App)

**CRITICAL:** The `VITE_API_BASE_URL` environment variable must remain **commented out** in `frontend/.env` to ensure the proxy works correctly. If this is set, ALL requests will bypass the proxy and go to a single backend.

---

## Project Structure

```
feature-frontend/
├── backend/                      # Auth Backend (Port 8000)
│   ├── auth/
│   │   ├── api/
│   │   │   ├── deps.py          # Dependency injection (JWT validation)
│   │   │   └── routes.py        # Auth API endpoints
│   │   ├── email/
│   │   │   ├── tasks.py         # Celery email tasks
│   │   │   └── templates.py     # Email HTML templates
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── service/             # Business logic layer
│   │       ├── auth_service.py        # Login, 2FA, tokens
│   │       ├── registration_service.py # User registration
│   │       └── password_reset_service.py # Password reset flow
│   ├── core/
│   │   └── config.py            # Application configuration
│   ├── db/
│   │   ├── models/              # SQLAlchemy ORM models
│   │   └── session.py           # Database session management
│   ├── redis/
│   │   └── client.py            # Redis connection
│   ├── security/
│   │   ├── jwt_service.py       # JWT token generation/validation
│   │   ├── password.py          # Argon2 password hashing
│   │   ├── turnstile.py         # Cloudflare Turnstile verification
│   │   └── keys/                # JWT signing keys (NEVER commit!)
│   │       ├── current.json     # Active ES256 key
│   │       └── next.json        # Next rotation key
│   ├── migrations/              # Alembic database migrations
│   ├── scripts/                 # Utility scripts
│   ├── app.py                   # FastAPI app entry point
│   └── .env                     # Backend configuration (NEVER commit!)
│
├── app/                         # Main Dashboard App (Port 3000)
│   ├── main.py                  # FastAPI app entry point
│   ├── workers/                 # Celery workers for jobs
│   ├── models/                  # Shared models
│   └── routes/                  # Dashboard API routes
│
├── frontend/                    # React + TypeScript Frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── lib/
│   │   │   └── api.ts           # API client (uses Vite proxy)
│   │   ├── pages/               # Route pages
│   │   └── contexts/            # React contexts (auth, etc.)
│   ├── vite.config.ts           # Vite proxy configuration
│   └── .env                     # Frontend config (Turnstile keys)
│
├── .env                         # Root env (Main Dashboard config)
├── .vscode/
│   └── launch.json              # VSCode debug configurations
└── docker-compose.yml           # Local infrastructure (Postgres, Redis)
```

---

## Core Components

### 1. Authentication Backend (`backend/`)

**Purpose:** Isolated, secure authentication service handling user identity, sessions, and security.

**Key Responsibilities:**
- User registration with email verification
- Login with 2FA support (TOTP)
- JWT access/refresh token management
- Password reset via email
- Session management with device tracking
- Rate limiting per IP and per account
- Recovery code generation for 2FA bypass

**Technology Stack:**
- FastAPI for REST API
- SQLAlchemy ORM with PostgreSQL
- Pydantic for validation
- Argon2id for password hashing
- ES256 JWT signatures
- Redis for rate limiting and temp storage
- Celery for async email tasks

### 2. Main Dashboard App (`app/`)

**Purpose:** Original orchestrator application for job management and feature processing.

**Key Responsibilities:**
- Job scheduling and execution
- Task management
- File processing
- Health monitoring
- WebSocket real-time updates

**Technology Stack:**
- FastAPI
- Celery workers
- WebSocket support

### 3. Frontend (`frontend/`)

**Purpose:** React-based SPA with TypeScript and Vite.

**Key Features:**
- Authentication flows (login, register, 2FA, password reset)
- Dashboard for job management
- Real-time updates via WebSocket
- Responsive design with Tailwind CSS
- Cloudflare Turnstile bot protection

---

## Authentication & Authorization System

### User Registration Flow

```
1. User submits registration form
   ↓
2. Turnstile token verified (bot protection)
   ↓
3. Rate limit check (10 registrations/IP/hour)
   ↓
4. Password validated (min 12 chars, complexity)
   ↓
5. Email uniqueness check
   ↓
6. User created with status='pending_verification'
   ↓
7. HMAC verification token generated
   ↓
8. Celery task queued to send verification email
   ↓
9. User clicks email link
   ↓
10. Token validated, user status → 'active'
```

**Implementation:** `backend/auth/service/registration_service.py`

### Login Flow

```
1. User submits email + password
   ↓
2. Rate limit check (10/IP/hour, 5/account/hour)
   ↓
3. User lookup by email
   ↓
4. Password verified with Argon2
   ↓
5. Account status check (active? suspended?)
   ↓
6. If 2FA enabled:
   │  → Generate challenge_id
   │  → Store in Redis (5 min TTL)
   │  → Return {requires_2fa: true, challenge_id}
   │  → Wait for /2fa/verify with TOTP code
   ↓
7. If no 2FA or 2FA verified:
   │  → Generate JWT access token (7 min TTL)
   │  → Generate JWT refresh token (30 day TTL)
   │  → Create Session record in DB
   │  → Return tokens
```

**Implementation:** `backend/auth/service/auth_service.py:login_user()`

### JWT Token Management

**Token Types:**

1. **Access Token**
   - Type: `access`
   - TTL: 420 seconds (7 minutes)
   - Payload: `sub` (user_id), `email`, `roles`, `type`, `exp`, `iat`, `iss`, `aud`
   - Used for API authentication

2. **Refresh Token**
   - Type: `refresh`
   - TTL: 2,592,000 seconds (30 days)
   - Payload: `sub` (user_id), `session_id`, `type`, `exp`, `iat`, `iss`, `aud`
   - Used to obtain new access tokens

**JWT Configuration:**
- Algorithm: ES256 (ECDSA with P-256 curve)
- Issuer: `feature-auth`
- Audience: `feature-auth-clients`
- Key rotation support with `current`, `next`, `previous` keys
- Grace period: 24 hours for previous key acceptance

**Key Files:**
- `backend/security/keys/current.json` - Active signing key
- `backend/security/keys/next.json` - Next rotation key
- `backend/security/keys/previous.json` - Previous key (grace period)

**⚠️ SECURITY:** Never commit these files to Git! They contain private keys.

### Token Refresh Flow

```
1. Client sends refresh_token
   ↓
2. JWT signature validated
   ↓
3. Session lookup by session_id from token
   ↓
4. Session checks:
   │  - Not revoked?
   │  - Not expired?
   │  - User active?
   ↓
5. Invalidate old session
   ↓
6. Create new session
   ↓
7. Issue new access + refresh tokens
   ↓
8. Return new tokens
```

**Implementation:** `backend/auth/service/auth_service.py:refresh_tokens()`

### Password Reset Flow

```
1. User requests password reset (email)
   ↓
2. Rate limit check (3/IP/hour)
   ↓
3. User lookup (timing-safe)
   ↓
4. Generate HMAC-SHA256 token
   ↓
5. Store in password_resets table (1 hour TTL)
   ↓
6. Celery task sends email with reset link
   ↓
7. User clicks link with token
   ↓
8. Token validated (not expired? not used?)
   ↓
9. New password validated
   ↓
10. Password updated with Argon2
   ↓
11. All password_resets for user purged
   ↓
12. Redirect to login
```

**Implementation:** `backend/auth/service/password_reset_service.py`

### 2FA (TOTP) Management

**Enable 2FA:**
1. POST `/v1/auth/2fa/enable-init` → Returns QR code + secret
2. User scans QR code in authenticator app
3. POST `/v1/auth/2fa/enable-complete` with TOTP code
4. If valid, 2FA enabled + recovery codes generated

**Verify 2FA During Login:**
1. After password verification, if 2FA enabled
2. POST `/v1/auth/2fa/verify` with challenge_id + TOTP code
3. If valid, issue tokens

**Recovery Login:**
1. POST `/v1/auth/recovery-login` with recovery code
2. Recovery code validated and consumed
3. Tokens issued

**Implementation:** `backend/auth/service/auth_service.py`

### Session Management

**Session Table Fields:**
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `refresh_token_hash` - SHA-256 hash of refresh token
- `ip_address` - Client IP at creation
- `user_agent` - Client user agent
- `created_at`, `expires_at`, `last_used_at`
- `revoked_at` - If manually revoked

**Session Lifecycle:**
- Created on successful login
- Updated on token refresh
- Automatically expired after 30 days
- Can be manually revoked via logout

---

## Database Schema

### Core Tables

#### `users`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- 'pending_verification', 'active', 'suspended'
    email_verified_at TIMESTAMP,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),  -- Encrypted TOTP secret
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
```

#### `user_roles`
```sql
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user', 'admin', 'pro'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);
```

#### `sessions`
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

#### `recovery_codes`
```sql
CREATE TABLE recovery_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    code_hash VARCHAR(255) NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
```

#### `password_resets`
```sql
CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    ip_address VARCHAR(45)
);

CREATE INDEX idx_password_resets_token_hash ON password_resets(token_hash);
CREATE INDEX idx_password_resets_expires_at ON password_resets(expires_at);
```

### Encryption at Rest

Sensitive fields are encrypted using **AES-256-GCM** with key rotation support:

- `users.mfa_secret` - TOTP secrets
- Future: PII fields, API keys, etc.

**Configuration:**
- `ENCRYPTION_KEYS` - JSON dict of key_id → base64 key
- `ENCRYPTION_KEY_ACTIVE` - Current active key ID

**Implementation:** Field-level encryption utilities in `backend/security/encryption.py` (if implemented)

---

## API Routes Reference

### Auth Backend (`/v1/auth/*`)

#### Public Endpoints (No Auth Required)

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/v1/auth/register` | Register new user | 10/IP/hour |
| POST | `/v1/auth/resend-verification` | Resend verification email | 5/account/hour |
| GET | `/v1/auth/verify-email?token=` | Verify email via token | None |
| POST | `/v1/auth/login` | Login with email/password | 10/IP/hour, 5/account/hour |
| POST | `/v1/auth/2fa/verify` | Verify TOTP code during login | 10/challenge/5min |
| POST | `/v1/auth/refresh` | Refresh access token | 20/IP/hour |
| POST | `/v1/auth/logout` | Logout and revoke session | None |
| POST | `/v1/auth/recovery-login` | Login with recovery code | 5/account/hour |
| POST | `/v1/auth/forgot-password` | Request password reset | 3/IP/hour |
| POST | `/v1/auth/reset-password` | Reset password with token | 5/IP/hour |

#### Protected Endpoints (Requires JWT Access Token)

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| GET | `/v1/auth/me` | Get current user info | 60/user/min |
| POST | `/v1/auth/2fa/enable-init` | Start 2FA setup | 5/user/hour |
| POST | `/v1/auth/2fa/enable-complete` | Complete 2FA setup | 5/user/hour |
| POST | `/v1/auth/2fa/disable` | Disable 2FA | 3/user/hour |

### Dashboard Backend (`/api/*`, `/jobs/*`, `/tasks/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/env` | Environment info |
| GET | `/api/models` | List available models |
| POST | `/jobs` | Create new job |
| GET | `/jobs` | List jobs |
| GET | `/jobs/{id}` | Get job details |
| DELETE | `/jobs/{id}` | Cancel job |
| GET | `/tasks` | List tasks |
| WS | `/ws` | WebSocket connection |

---

## Security & Rate Limiting

### Rate Limiting Strategy

**Implementation:** Redis-based with sliding window counters

**Rate Limit Scopes:**

1. **IP-based:**
   - Key: `rate_limit:login:ip:{ip_address}`
   - Limit: 10 requests/hour
   - Protects against brute force from single IP

2. **Account-based:**
   - Key: `rate_limit:login:account:{email}`
   - Limit: 5 requests/hour
   - Protects against distributed brute force

3. **Challenge-based (2FA):**
   - Key: `auth:2fa_challenge:{challenge_id}`
   - Limit: 10 attempts/5 minutes
   - Prevents TOTP brute force

4. **Registration:**
   - Key: `rate_limit:register:ip:{ip_address}`
   - Limit: 10 registrations/hour
   - Prevents bulk account creation

5. **Password Reset:**
   - Key: `rate_limit:password_reset:ip:{ip_address}`
   - Limit: 3 requests/hour
   - Prevents abuse of email system

**Configuration:**
```python
# backend/core/config.py
RATE_LIMIT_DEFAULT_REQUESTS = 60
RATE_LIMIT_DEFAULT_WINDOW_SECONDS = 60
RATE_LIMIT_ALLOWLIST = []  # IPs to exempt
RATE_LIMIT_DENYLIST = []   # IPs to block
```

### Password Security

**Hashing:** Argon2id with configurable parameters

**Default Configuration:**
```python
ARGON2_TIME_COST = 3         # Iterations
ARGON2_MEMORY_COST = 65536   # Memory in KB (64 MB)
ARGON2_PARALLELISM = 4       # CPU threads
ARGON2_HASH_LEN = 32         # Output length
```

**Password Validation Rules:**
- Minimum 12 characters
- Must contain: uppercase, lowercase, digit, special character
- Checked against common password lists (optional)

**Implementation:** `backend/security/password.py`

### Bot Protection

**Cloudflare Turnstile** integration on:
- Registration
- Login
- Password reset

**Configuration:**
```bash
# backend/.env
TURNSTILE_SECRET_KEY=your_secret_key

# frontend/.env
VITE_TURNSTILE_SITE_KEY=1x00000000000000000000AA  # Dev key
```

### CORS & Security Headers

**CORS Configuration:**
```python
# backend/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Security Headers:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy` (configured per app)

---

## Email & Notifications

### Email Infrastructure

**SMTP Configuration:**
```python
SMTP_HOST = "smtp.ionos.de"
SMTP_PORT = 587
SMTP_USE_TLS = True
SMTP_USER = "your_email@domain.com"
SMTP_PASS = "your_password"
EMAIL_FROM_ADDRESS = "noreply@yourdomain.com"
EMAIL_FROM_NAME = "Feature Auth"
```

### Celery Task Queue

**Broker:** Redis
**Workers:** Dedicated Celery workers for async tasks

**Email Tasks:**

1. `send_verification_email_task(email, token, base_url)`
   - Sends registration verification email
   - Template: HTML with button link

2. `send_password_reset_email_task(email, token, base_url)`
   - Sends password reset email
   - Template: HTML with reset link

**Worker Command:**
```bash
celery -A backend.auth.email.tasks worker --loglevel=info
```

### Email Templates

**Location:** `backend/auth/email/templates.py`

**Templates:**
- `render_verification_email(verification_url)` - Registration
- `render_password_reset_email(reset_url)` - Password reset

**Future:** Template system with i18n support, branded layouts

---

## Configuration Management

### Environment Files

**1. Root `.env` (Main Dashboard)**
```bash
# Original orchestrator app configuration
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
# ... other dashboard-specific vars
```

**2. `backend/.env` (Auth Backend)**
```bash
# Backend-specific configuration
ENVIRONMENT=development
DEBUG=False

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/feature_db

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Keys (CRITICAL: Use file paths, not inline JSON)
JWT_JWK_CURRENT=/home/chris/projects/feature-frontend/backend/security/keys/current.json
JWT_JWK_NEXT=/home/chris/projects/feature-frontend/backend/security/keys/next.json
JWT_JWK_PREVIOUS=
JWT_ISSUER=feature-auth
JWT_AUDIENCE=feature-auth-clients
JWT_ACCESS_TTL_SECONDS=420
JWT_REFRESH_TTL_SECONDS=2592000
JWT_PREVIOUS_GRACE_SECONDS=86400

# Password Hashing
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=4
ARGON2_HASH_LEN=32

# Turnstile
TURNSTILE_SECRET_KEY=your_secret

# Email
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=Feature Auth
FRONTEND_BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
EMAIL_VERIFICATION_SECRET=your_secret_key_here

# SMTP
SMTP_HOST=smtp.ionos.de
SMTP_PORT=587
SMTP_USE_TLS=True
SMTP_USER=your_email
SMTP_PASS=your_password

# Admin (initial setup)
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure_password

# Encryption
ENCRYPTION_KEYS={"key1":"base64_encoded_key"}
ENCRYPTION_KEY_ACTIVE=key1

# Rate Limiting
RATE_LIMIT_DEFAULT_REQUESTS=60
RATE_LIMIT_DEFAULT_WINDOW_SECONDS=60
RATE_LIMIT_ALLOWLIST=
RATE_LIMIT_DENYLIST=

# Observability
SERVICE_NAME=auth
SERVICE_VERSION=0.1.0
LOG_LEVEL=INFO
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**3. `frontend/.env` (Frontend)**
```bash
# CRITICAL: Keep VITE_API_BASE_URL commented out!
# VITE_API_BASE_URL=http://localhost:8000

# Turnstile
VITE_TURNSTILE_SITE_KEY=1x00000000000000000000AA
```

### Configuration Loading

**Backend:** Uses `pydantic-settings` with explicit env file path

```python
# backend/core/config.py
@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / "backend" / ".env"
    return AppConfig(_env_file=str(env_file))
```

**⚠️ CRITICAL:** Must use `_env_file` parameter to prevent loading root `.env`

---

## Development Workflow

### Local Development Setup

**1. Prerequisites:**
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

**2. Initial Setup:**

```bash
# Clone repository
git clone <repo_url>
cd feature-frontend

# Backend setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create backend/.env (copy from template)
cp backend/.env.example backend/.env
# Edit backend/.env with your configuration

# Generate JWT keys
python backend/scripts/jwk_generate.py

# Database migrations
alembic upgrade head

# Frontend setup
cd frontend
npm install
# Create frontend/.env (ensure VITE_API_BASE_URL is commented!)
cp .env.example .env
```

**3. Start Infrastructure:**

```bash
# Option A: Docker Compose
docker-compose up -d postgres redis

# Option B: Local installations
# Start PostgreSQL and Redis manually
```

**4. Start Services:**

```bash
# Terminal 1: Auth Backend
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Main Dashboard
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 3000 --reload

# Terminal 3: Celery Worker
source .venv/bin/activate
celery -A backend.auth.email.tasks worker --loglevel=info

# Terminal 4: Frontend
cd frontend
npm run dev
```

**5. Access:**
- Frontend: http://localhost:5173
- Auth API Docs: http://localhost:8000/docs
- Dashboard API Docs: http://localhost:8000/docs

### VSCode Debugging

**Launch Configurations:**

```json
{
  "name": "Backend (Auth API)",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["backend.app:app", "--reload", "--port", "8000"],
  "env": {"PYTHONPATH": "${workspaceFolder}"},
  "envFile": "${workspaceFolder}/backend/.env",
  "jinja": true,
  "justMyCode": false
}
```

**Compound Launch:**
- "Run All Services" - Starts all backends + frontend simultaneously

### Database Migrations

**Create Migration:**
```bash
alembic revision --autogenerate -m "Add user_subscriptions table"
```

**Apply Migrations:**
```bash
alembic upgrade head
```

**Rollback:**
```bash
alembic downgrade -1
```

**Migration Location:** `backend/migrations/versions/`

### Testing

**Run Backend Tests:**
```bash
pytest backend/tests/
```

**Run Frontend Tests:**
```bash
cd frontend
npm run test
```

**Coverage:**
```bash
pytest --cov=backend --cov-report=html
```

---

## Deployment & Operations

### Production Considerations

**1. Environment Variables:**
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Never commit `.env` files
- Rotate JWT keys regularly

**2. Database:**
- Use connection pooling (SQLAlchemy pool_size, max_overflow)
- Enable SSL/TLS for connections
- Regular backups with point-in-time recovery

**3. Redis:**
- Use Redis Cluster for high availability
- Enable persistence (AOF + RDB)
- Separate Redis instances for cache vs. rate limiting

**4. Application Servers:**
- Use Gunicorn with Uvicorn workers
- Example: `gunicorn backend.app:app -w 4 -k uvicorn.workers.UvicornWorker`
- Configure worker count based on CPU cores

**5. HTTPS/TLS:**
- Use reverse proxy (Nginx, Caddy, CloudFlare)
- Enforce HTTPS redirects
- Configure HSTS headers

**6. Monitoring:**
- OpenTelemetry for distributed tracing
- Prometheus metrics
- Structured logging with log aggregation
- Health check endpoints

**7. Rate Limiting:**
- Consider using Redis Cluster or dedicated rate limit service
- Implement distributed rate limiting for multi-instance deployments

### Docker Deployment

**Backend Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY app/ ./app/
CMD ["gunicorn", "backend.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

**Frontend Dockerfile:**
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### Health Checks

**Auth Backend:**
```python
@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth"}
```

**Dashboard:**
```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

### Logging & Observability

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("user.login", user_id=user.id, ip=ip_address)
```

**OpenTelemetry:**
- Traces for request flows
- Spans for external calls (DB, Redis, SMTP)
- Metrics for request counts, latency, errors

**Configuration:**
```python
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
SERVICE_NAME=auth
SERVICE_VERSION=0.1.0
```

---

## Testing Strategy

### Unit Tests

**Backend:**
- Test service layer functions in isolation
- Mock external dependencies (DB, Redis, email)
- Example: `backend/tests/test_auth_service.py`

```python
def test_login_user_success(mock_db):
    # Arrange
    user = create_test_user(email="test@example.com")

    # Act
    response = login_user(db=mock_db, email="test@example.com", password="password")

    # Assert
    assert response.access_token is not None
```

### Integration Tests

**Backend:**
- Test API endpoints with test database
- Use TestClient from FastAPI

```python
from fastapi.testclient import TestClient

def test_register_endpoint():
    client = TestClient(app)
    response = client.post("/v1/auth/register", json={
        "email": "test@example.com",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
```

### E2E Tests

**Frontend:**
- Use Playwright or Cypress
- Test full user flows (registration → verification → login → 2FA)

### Test Database

**Strategy:** Use separate test database with automatic cleanup

```python
# conftest.py
@pytest.fixture
def test_db():
    engine = create_engine("postgresql://test_db")
    Base.metadata.create_all(engine)
    yield SessionLocal()
    Base.metadata.drop_all(engine)
```

---

## Security Best Practices

### DO's ✅

1. **Always use parameterized queries** (SQLAlchemy ORM handles this)
2. **Validate all user input** with Pydantic schemas
3. **Use HTTPS in production**
4. **Rotate JWT keys regularly** (quarterly recommended)
5. **Hash sensitive data** (passwords with Argon2, tokens with SHA-256)
6. **Encrypt PII at rest** (AES-256-GCM)
7. **Rate limit all public endpoints**
8. **Use timing-safe comparisons** for tokens/passwords
9. **Log security events** (failed logins, password changes)
10. **Keep dependencies updated**

### DON'Ts ❌

1. **Never commit secrets to Git** (.env, JWT keys, API keys)
2. **Never log sensitive data** (passwords, tokens, PII)
3. **Never trust client input** (always validate server-side)
4. **Never use weak JWT algorithms** (HS256 with shared secrets)
5. **Never store passwords in plain text**
6. **Never expose internal errors to users**
7. **Never skip rate limiting on auth endpoints**
8. **Never use sequential IDs for sensitive resources**

### Incident Response Plan

**1. Suspected Token Compromise:**
- Rotate JWT keys immediately
- Revoke all sessions
- Force password reset for affected users
- Review access logs

**2. Database Breach:**
- Assess data exposure
- Notify affected users
- Force password reset for all users
- Review and patch vulnerability
- Consider encryption key rotation

**3. Rate Limit Bypass:**
- Review rate limit logic
- Check for IP spoofing
- Update Redis rate limit keys
- Consider IP allowlist/denylist

---

## Troubleshooting Guide

### Common Issues

**1. "JWK is missing 'kid'"**
- **Cause:** JWT key file doesn't have `kid` field
- **Fix:** Regenerate keys with `backend/scripts/jwk_generate.py`

**2. "All requests going to wrong backend"**
- **Cause:** `VITE_API_BASE_URL` set in `frontend/.env`
- **Fix:** Comment out `VITE_API_BASE_URL` to use Vite proxy

**3. "Config loading wrong .env file"**
- **Cause:** Pydantic loading both root and backend `.env`
- **Fix:** Ensure `get_settings()` uses `_env_file` parameter

**4. "Rate limit triggered incorrectly"**
- **Cause:** Redis keys not expiring or IP detection failing
- **Fix:** Check Redis TTL, verify `X-Forwarded-For` header

**5. "Email not sending"**
- **Cause:** Celery worker not running or SMTP config wrong
- **Fix:** Check worker logs, test SMTP credentials

**6. "Database migration fails"**
- **Cause:** Schema conflict or manual DB changes
- **Fix:** Review migration, consider manual SQL fix

### Debug Tools

**Clear Rate Limits:**
```python
# scripts/clear_rate_limits.py
import redis
r = redis.from_url("redis://localhost:6379/0")
keys = r.keys("rate_limit:*")
r.delete(*keys)
```

**Test JWT Loading:**
```bash
python test_jwt_loading.py
```

**Test Login:**
```bash
python test_login.py
```

**Check Redis Keys:**
```bash
redis-cli
> KEYS *
> GET rate_limit:login:ip:127.0.0.1
```

---

## Glossary

- **2FA:** Two-Factor Authentication (TOTP)
- **Argon2:** Password hashing algorithm (winner of PHC)
- **CORS:** Cross-Origin Resource Sharing
- **ES256:** ECDSA signature with P-256 curve and SHA-256
- **HMAC:** Hash-based Message Authentication Code
- **JWT:** JSON Web Token
- **ORM:** Object-Relational Mapping (SQLAlchemy)
- **TOTP:** Time-based One-Time Password (RFC 6238)
- **TTL:** Time To Live
- **Turnstile:** Cloudflare bot protection service

---

## Change Log

### Version 0.1.0 (Current)
- Initial authentication system implementation
- User registration with email verification
- Login with 2FA support
- JWT token management with ES256
- Password reset flow
- Session management
- Rate limiting
- Dual backend architecture
- Vite proxy routing

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Argon2 Specification](https://github.com/P-H-C/phc-winner-argon2)

---

**Last Updated:** 2025-10-08
**Maintained By:** Development Team
**Version:** 1.0.0
