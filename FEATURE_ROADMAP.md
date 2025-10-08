# Feature Roadmap & Implementation Plan

## Table of Contents

1. [Current System Status](#current-system-status)
2. [Protected Areas (DO NOT TOUCH)](#protected-areas-do-not-touch)
3. [Phase 1: Subscription & User Management](#phase-1-subscription--user-management)
4. [Phase 2: Admin Backend](#phase-2-admin-backend)
5. [Phase 3: Enhanced Rate Limiting & Quotas](#phase-3-enhanced-rate-limiting--quotas)
6. [Phase 4: Billing Integration](#phase-4-billing-integration)
7. [Phase 5: Advanced Features](#phase-5-advanced-features)
8. [Implementation Guidelines](#implementation-guidelines)
9. [Testing Requirements](#testing-requirements)

---

## Current System Status

### ✅ Completed Features

- [x] User registration with email verification
- [x] Login with username/password
- [x] Two-factor authentication (TOTP)
- [x] Password reset via email
- [x] JWT access/refresh token system
- [x] Session management with device tracking
- [x] Rate limiting (IP-based and account-based)
- [x] Email delivery via Celery
- [x] Dual backend architecture (Auth + Dashboard)
- [x] Vite proxy routing
- [x] Basic role system (`user`, `admin`)
- [x] Recovery codes for 2FA bypass

### 🔄 Current Limitations

- No subscription/plan management (all users treated equally)
- No differentiated rate limits or quotas by plan
- No admin interface for user management
- No billing/payment integration
- No usage tracking or analytics
- No audit logging
- No user impersonation for support
- No bulk user operations

---

## Protected Areas (DO NOT TOUCH)

### ⚠️ CRITICAL: These areas are working and MUST NOT be modified unless explicitly approved

#### 1. Authentication Core (`backend/auth/`)

**Protected Files:**
- `backend/auth/api/routes.py` - Auth API endpoints
- `backend/auth/service/auth_service.py` - Login, 2FA, token management
- `backend/auth/service/registration_service.py` - User registration flow
- `backend/auth/service/password_reset_service.py` - Password reset flow
- `backend/security/jwt_service.py` - JWT token generation/validation
- `backend/security/password.py` - Argon2 password hashing

**Why Protected:**
These files handle critical security functions. Any bugs could compromise user accounts or cause authentication failures.

**Modification Policy:**
- NO changes without explicit approval
- Must have full test coverage before any changes
- Require security review for any modifications

#### 2. Configuration System

**Protected Files:**
- `backend/core/config.py` - Configuration loading
- `backend/.env` - Backend environment variables
- `.env` (root) - Dashboard environment variables
- `frontend/.env` - Frontend environment variables

**Why Protected:**
The dual-backend architecture requires careful configuration management. Changes could break the routing or cause config conflicts.

**Modification Policy:**
- NO changes to env file loading logic
- New config variables are OK (additive only)
- Must maintain backward compatibility

#### 3. Database Models (Existing)

**Protected Files:**
- `backend/db/models/user.py` - User model
- `backend/db/models/session.py` - Session model
- `backend/db/models/recovery_code.py` - Recovery code model
- `backend/db/models/password_reset.py` - Password reset model

**Why Protected:**
Existing tables have data in production. Schema changes require careful migration planning.

**Modification Policy:**
- NO destructive changes (dropping columns/tables)
- Additive changes OK (new columns with defaults, new tables)
- Must provide Alembic migration
- Must handle data migration for existing rows

#### 4. Frontend Routing & Proxy

**Protected Files:**
- `frontend/vite.config.ts` - Vite proxy configuration
- `frontend/src/lib/api.ts` - API client

**Why Protected:**
The Vite proxy is critical for routing requests to the correct backend. Breaking this breaks the entire application.

**Modification Policy:**
- NO changes to proxy routing logic
- NO setting `VITE_API_BASE_URL` in `frontend/.env`
- New API endpoints are OK
- Must test both auth and dashboard requests

#### 5. Database Session Management

**Protected Files:**
- `backend/db/session.py` - Database session factory

**Why Protected:**
Shared by both backends. Changes could affect connection pooling or transaction management.

**Modification Policy:**
- NO changes without testing both backends
- Connection pool settings can be tuned

---

## Phase 1: Subscription & User Management

**Priority:** HIGH
**Estimated Time:** 2-3 weeks
**Dependencies:** None

### Overview

Implement a subscription/plan system to differentiate between free and pro users, with configurable quotas and limits per plan.

### Features

#### 1.1 Subscription Plans Table

**New Database Table: `subscription_plans`**

```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,  -- 'free', 'pro', 'enterprise'
    display_name VARCHAR(255) NOT NULL,  -- 'Free Plan', 'Pro Plan'
    description TEXT,
    price_cents INTEGER NOT NULL,  -- Price in cents (0 for free)
    billing_period VARCHAR(20),  -- 'monthly', 'yearly', null for free

    -- Feature flags
    features JSONB NOT NULL,  -- {"api_access": true, "priority_support": false, ...}

    -- Limits & Quotas
    rate_limit_multiplier DECIMAL(4,2) DEFAULT 1.0,  -- 1.0 = normal, 2.0 = double
    max_jobs_per_month INTEGER,
    max_storage_mb INTEGER,
    max_api_calls_per_day INTEGER,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed data
INSERT INTO subscription_plans (name, display_name, price_cents, features) VALUES
('free', 'Free Plan', 0, '{"api_access": true, "priority_support": false, "custom_models": false}'),
('pro', 'Pro Plan', 1999, '{"api_access": true, "priority_support": true, "custom_models": true, "advanced_analytics": true}'),
('enterprise', 'Enterprise Plan', 9999, '{"api_access": true, "priority_support": true, "custom_models": true, "advanced_analytics": true, "dedicated_support": true}');
```

**New Database Table: `user_subscriptions`**

```sql
CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES subscription_plans(id),

    status VARCHAR(50) NOT NULL,  -- 'active', 'cancelled', 'expired', 'trial'

    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,  -- NULL for lifetime/free
    cancelled_at TIMESTAMP,

    -- Usage tracking
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,

    -- Payment info (for future billing integration)
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_active_subscription UNIQUE (user_id, status)
        WHERE status = 'active'
);

CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_expires_at ON user_subscriptions(expires_at);
```

**Migration Command:**
```bash
alembic revision --autogenerate -m "Add subscription tables"
alembic upgrade head
```

#### 1.2 Usage Tracking Table

**New Database Table: `user_usage`**

```sql
CREATE TABLE user_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Period tracking
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,

    -- Usage counters
    api_calls INTEGER DEFAULT 0,
    jobs_created INTEGER DEFAULT 0,
    storage_used_mb INTEGER DEFAULT 0,
    compute_minutes INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_user_period UNIQUE (user_id, period_start)
);

CREATE INDEX idx_user_usage_user_id ON user_usage(user_id);
CREATE INDEX idx_user_usage_period ON user_usage(period_start, period_end);
```

#### 1.3 Backend Services

**New File: `backend/subscription/service.py`**

```python
"""Subscription management service."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from backend.db.models.user import User
from backend.db.models.subscription_plan import SubscriptionPlan
from backend.db.models.user_subscription import UserSubscription


def get_user_subscription(db: Session, user_id: UUID) -> UserSubscription | None:
    """Get active subscription for user."""
    return db.query(UserSubscription).filter(
        UserSubscription.user_id == user_id,
        UserSubscription.status == 'active',
    ).first()


def get_user_plan(db: Session, user_id: UUID) -> SubscriptionPlan:
    """Get subscription plan for user (defaults to free)."""
    subscription = get_user_subscription(db, user_id)
    if subscription:
        return subscription.plan

    # Default to free plan
    return db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == 'free'
    ).first()


def has_feature(db: Session, user_id: UUID, feature: str) -> bool:
    """Check if user has access to a feature."""
    plan = get_user_plan(db, user_id)
    return plan.features.get(feature, False)


def get_rate_limit_multiplier(db: Session, user_id: UUID) -> float:
    """Get rate limit multiplier for user's plan."""
    plan = get_user_plan(db, user_id)
    return plan.rate_limit_multiplier or 1.0


def upgrade_user_plan(
    db: Session,
    user_id: UUID,
    plan_name: str,
    duration_days: int = 30,
) -> UserSubscription:
    """Upgrade user to a new plan."""
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name == plan_name
    ).first()

    if not plan:
        raise ValueError(f"Plan {plan_name} not found")

    # Cancel existing subscription
    existing = get_user_subscription(db, user_id)
    if existing:
        existing.status = 'cancelled'
        existing.cancelled_at = datetime.utcnow()

    # Create new subscription
    subscription = UserSubscription(
        user_id=user_id,
        plan_id=plan.id,
        status='active',
        started_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=duration_days),
        current_period_start=datetime.utcnow(),
        current_period_end=datetime.utcnow() + timedelta(days=duration_days),
    )
    db.add(subscription)
    db.commit()
    return subscription


def check_quota(db: Session, user_id: UUID, quota_type: str) -> tuple[bool, int, int]:
    """
    Check if user is within quota limits.

    Returns:
        (is_within_quota, current_usage, limit)
    """
    plan = get_user_plan(db, user_id)
    usage = get_current_period_usage(db, user_id)

    limits = {
        'jobs': plan.max_jobs_per_month,
        'storage': plan.max_storage_mb,
        'api_calls': plan.max_api_calls_per_day,
    }

    current = {
        'jobs': usage.jobs_created if usage else 0,
        'storage': usage.storage_used_mb if usage else 0,
        'api_calls': usage.api_calls if usage else 0,
    }

    limit = limits.get(quota_type)
    if limit is None:
        return True, current.get(quota_type, 0), -1  # Unlimited

    return current.get(quota_type, 0) < limit, current.get(quota_type, 0), limit


def increment_usage(db: Session, user_id: UUID, metric: str, amount: int = 1):
    """Increment usage metric for current period."""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate period end (first day of next month)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)

    usage = db.query(UserUsage).filter(
        UserUsage.user_id == user_id,
        UserUsage.period_start == period_start,
    ).first()

    if not usage:
        usage = UserUsage(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(usage)

    # Increment the specific metric
    if metric == 'api_calls':
        usage.api_calls += amount
    elif metric == 'jobs':
        usage.jobs_created += amount
    elif metric == 'storage':
        usage.storage_used_mb += amount
    elif metric == 'compute':
        usage.compute_minutes += amount

    db.commit()


def get_current_period_usage(db: Session, user_id: UUID):
    """Get usage for current billing period."""
    now = datetime.utcnow()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return db.query(UserUsage).filter(
        UserUsage.user_id == user_id,
        UserUsage.period_start == period_start,
    ).first()
```

#### 1.4 API Endpoints

**New File: `backend/subscription/api/routes.py`**

```python
"""Subscription API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User
from backend.db.session import get_db
from backend.subscription import service
from backend.subscription.schemas import (
    SubscriptionResponse,
    UsageResponse,
    PlanListResponse,
)

router = APIRouter(prefix="/v1/subscription", tags=["subscription"])


@router.get("/me", response_model=SubscriptionResponse)
def get_my_subscription(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription."""
    subscription = service.get_user_subscription(db, current_user.id)
    plan = service.get_user_plan(db, current_user.id)

    return {
        "subscription": subscription,
        "plan": plan,
    }


@router.get("/usage", response_model=UsageResponse)
def get_my_usage(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Get current period usage."""
    usage = service.get_current_period_usage(db, current_user.id)
    plan = service.get_user_plan(db, current_user.id)

    return {
        "usage": usage,
        "limits": {
            "jobs": plan.max_jobs_per_month,
            "storage": plan.max_storage_mb,
            "api_calls": plan.max_api_calls_per_day,
        },
    }


@router.get("/plans", response_model=PlanListResponse)
def list_plans(db: Session = Depends(get_db)):
    """List all available subscription plans."""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).all()

    return {"plans": plans}
```

**Add to `backend/app.py`:**
```python
from backend.subscription.api.routes import router as subscription_router

app.include_router(subscription_router)
```

#### 1.5 Enhanced Rate Limiting

**Modify: `backend/auth/api/deps.py`**

Add plan-aware rate limiting:

```python
from backend.subscription.service import get_rate_limit_multiplier

def get_rate_limit(
    scope: str,
    base_limit: int,
    window_seconds: int,
    user: User | None = None,
    db: Session = None,
) -> int:
    """Get rate limit adjusted for user's plan."""
    if user and db:
        multiplier = get_rate_limit_multiplier(db, user.id)
        return int(base_limit * multiplier)
    return base_limit
```

#### 1.6 Quota Enforcement Middleware

**New File: `backend/middleware/quota.py`**

```python
"""Quota enforcement middleware."""

from fastapi import Request, HTTPException, status
from backend.subscription.service import check_quota, increment_usage


async def enforce_quota(request: Request, quota_type: str):
    """Check and enforce quota limits."""
    user = request.state.user  # Set by auth middleware
    db = request.state.db

    is_within, current, limit = check_quota(db, user.id, quota_type)

    if not is_within:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "message": f"You have exceeded your {quota_type} quota",
                "current": current,
                "limit": limit,
                "plan": "Consider upgrading to Pro for higher limits",
            }
        )
```

### Success Criteria

- [ ] Free and Pro plans defined in database
- [ ] Users have default free plan on registration
- [ ] Subscription status visible in `/v1/auth/me` response
- [ ] Usage tracking increments correctly
- [ ] Rate limits adjusted based on plan
- [ ] Quota enforcement blocks requests when exceeded
- [ ] API endpoints for viewing subscription and usage

### Testing Requirements

- [ ] Unit tests for subscription service functions
- [ ] Integration tests for quota enforcement
- [ ] Test plan upgrade/downgrade flows
- [ ] Test usage incrementing across period boundaries
- [ ] Test rate limit multiplier with different plans

---

## Phase 2: Admin Backend

**Priority:** HIGH
**Estimated Time:** 2-3 weeks
**Dependencies:** Phase 1

### Overview

Create a separate admin interface for user management, accessible only to hardcoded admin users. This will be a dedicated FastAPI app with its own routes.

### Features

#### 2.1 Admin User System

**Modify: `backend/db/models/user.py`**

Add admin flag:

```python
class User(Base):
    # ... existing fields ...
    is_superadmin = Column(Boolean, default=False, nullable=False)
```

**Migration:**
```bash
alembic revision --autogenerate -m "Add is_superadmin flag"
alembic upgrade head
```

**Set admin via SQL:**
```sql
UPDATE users SET is_superadmin = TRUE WHERE email = 'admin@example.com';
```

#### 2.2 Admin Authentication Dependency

**New File: `backend/admin/api/deps.py`**

```python
"""Admin authentication dependencies."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.api.deps import require_current_user
from backend.db.models.user import User
from backend.db.session import get_db


def require_admin(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Require user to be superadmin."""
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
```

#### 2.3 Admin API Routes

**New File: `backend/admin/api/routes.py`**

```python
"""Admin API routes for user management."""

from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.admin.api.deps import require_admin
from backend.db.models.user import User
from backend.db.session import get_db
from backend.admin.schemas import (
    UserListResponse,
    UserDetailResponse,
    UserUpdateRequest,
    RateLimitClearRequest,
    UserStatsResponse,
)
from backend.redis.client import get_redis_client

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    status: str | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users with filtering."""
    query = db.query(User)

    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))

    if status:
        query = query.filter(User.status == status)

    total = query.count()
    users = query.offset(skip).limit(limit).all()

    return {
        "users": users,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get detailed user information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Include subscription, usage, sessions
    subscription = get_user_subscription(db, user_id)
    usage = get_current_period_usage(db, user_id)
    sessions = db.query(Session).filter(
        Session.user_id == user_id,
        Session.revoked_at.is_(None),
    ).all()

    return {
        "user": user,
        "subscription": subscription,
        "usage": usage,
        "active_sessions": sessions,
    }


@router.patch("/users/{user_id}", response_model=UserDetailResponse)
def update_user(
    user_id: UUID,
    payload: UserUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (suspend, activate, change plan, etc.)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.status is not None:
        user.status = payload.status

    if payload.plan_name is not None:
        upgrade_user_plan(db, user_id, payload.plan_name)

    db.commit()
    return get_user(user_id, admin, db)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete user account (soft delete)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Soft delete: change status instead of actual deletion
    user.status = 'deleted'
    user.email = f"deleted_{user.id}@example.com"  # Free up email

    # Revoke all sessions
    db.query(Session).filter(
        Session.user_id == user_id,
        Session.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})

    db.commit()
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/revoke-sessions")
def revoke_all_sessions(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revoke all active sessions for a user."""
    count = db.query(Session).filter(
        Session.user_id == user_id,
        Session.revoked_at.is_(None),
    ).update({"revoked_at": datetime.utcnow()})

    db.commit()
    return {"message": f"Revoked {count} sessions"}


@router.post("/users/{user_id}/clear-rate-limits")
def clear_user_rate_limits(
    user_id: UUID,
    payload: RateLimitClearRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Clear rate limits for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    redis = get_redis_client()

    # Clear specified scopes or all
    scopes = payload.scopes or ['login', 'register', 'password_reset', '2fa']
    cleared = []

    for scope in scopes:
        # Clear account-based limits
        key = f"rate_limit:{scope}:account:{user.email}"
        if redis.delete(key):
            cleared.append(key)

    return {
        "message": "Rate limits cleared",
        "cleared_keys": cleared,
    }


@router.get("/stats", response_model=UserStatsResponse)
def get_platform_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get platform-wide statistics."""
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(
        User.status == 'active'
    ).scalar()

    pro_users = db.query(func.count(UserSubscription.id)).filter(
        UserSubscription.status == 'active',
        UserSubscription.plan.has(name='pro'),
    ).scalar()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "pro_users": pro_users,
        "free_users": active_users - pro_users,
    }


@router.get("/audit-log")
def get_audit_log(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get audit log (requires audit_events table from Phase 5)."""
    # TODO: Implement when audit logging is added
    return {"message": "Audit logging not yet implemented"}
```

**Add to `backend/app.py`:**
```python
from backend.admin.api.routes import router as admin_router

app.include_router(admin_router)
```

#### 2.4 Admin Frontend (Optional)

Create a simple admin dashboard at `/admin` route in frontend:

- User list with search/filter
- User detail view with subscription info
- Actions: Suspend, Delete, Clear rate limits, Revoke sessions
- Platform statistics dashboard

**Note:** Can be implemented as React Admin or similar library.

### Success Criteria

- [ ] Admin flag stored in database
- [ ] Only superadmins can access `/v1/admin/*` endpoints
- [ ] List users with pagination
- [ ] View detailed user info (subscription, usage, sessions)
- [ ] Suspend/activate user accounts
- [ ] Delete user accounts (soft delete)
- [ ] Clear rate limits for specific user
- [ ] Revoke all sessions for user
- [ ] View platform statistics

### Testing Requirements

- [ ] Test admin auth dependency blocks non-admins
- [ ] Test user listing with filters
- [ ] Test user suspension flow
- [ ] Test rate limit clearing
- [ ] Test session revocation

---

## Phase 3: Enhanced Rate Limiting & Quotas

**Priority:** MEDIUM
**Estimated Time:** 1-2 weeks
**Dependencies:** Phase 1

### Features

#### 3.1 Plan-Based Rate Limit Configuration

**Database Schema: Update `subscription_plans` table**

Add rate limit configuration JSONB:

```sql
ALTER TABLE subscription_plans
ADD COLUMN rate_limits JSONB DEFAULT '{
  "login": {"requests": 10, "window": 3600},
  "register": {"requests": 5, "window": 3600},
  "api": {"requests": 60, "window": 60},
  "jobs": {"requests": 10, "window": 3600}
}';

-- Pro plan: 5x limits
UPDATE subscription_plans SET rate_limits = '{
  "login": {"requests": 50, "window": 3600},
  "register": {"requests": 25, "window": 3600},
  "api": {"requests": 300, "window": 60},
  "jobs": {"requests": 50, "window": 3600}
}' WHERE name = 'pro';
```

#### 3.2 Dynamic Rate Limiting Middleware

**New File: `backend/middleware/rate_limit.py`**

```python
"""Dynamic rate limiting based on user plan."""

import time
from fastapi import Request, HTTPException, status
from backend.subscription.service import get_user_plan
from backend.redis.client import get_redis_client


def get_rate_limit_for_user(db, user_id: UUID, scope: str) -> tuple[int, int]:
    """Get rate limit config for user's plan."""
    plan = get_user_plan(db, user_id)
    config = plan.rate_limits.get(scope, {"requests": 60, "window": 60})
    return config["requests"], config["window"]


async def check_rate_limit(
    request: Request,
    scope: str,
    user_id: UUID | None = None,
    identifier: str | None = None,
):
    """Check rate limit with plan-aware limits."""
    redis = get_redis_client()
    db = request.state.db

    if user_id:
        limit, window = get_rate_limit_for_user(db, user_id, scope)
        key = f"rate_limit:{scope}:user:{user_id}"
    else:
        # Fallback to IP-based
        limit, window = 60, 60  # Default
        key = f"rate_limit:{scope}:ip:{identifier}"

    current = redis.get(key)
    if current is None:
        redis.setex(key, window, 1)
        return

    if int(current) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Rate limit exceeded for {scope}",
                "limit": limit,
                "window": window,
                "retry_after": redis.ttl(key),
            }
        )

    redis.incr(key)
```

#### 3.3 Job Quota Enforcement

**Modify: `app/routes/jobs.py` (Main Dashboard)**

Add quota check before job creation:

```python
from backend.subscription.service import check_quota, increment_usage

@router.post("/jobs")
def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Create new job with quota enforcement."""

    # Check quota
    is_within, current, limit = check_quota(db, current_user.id, 'jobs')
    if not is_within:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "quota_exceeded",
                "message": "You have reached your monthly job limit",
                "current": current,
                "limit": limit,
                "upgrade_url": f"{FRONTEND_URL}/pricing",
            }
        )

    # Create job
    job = create_job_internal(payload)

    # Increment usage
    increment_usage(db, current_user.id, 'jobs', 1)

    return job
```

### Success Criteria

- [ ] Rate limits configurable per plan in database
- [ ] Users see different rate limits based on plan
- [ ] Job creation blocked when quota exceeded
- [ ] Upgrade prompt shown when quota exceeded
- [ ] API calls tracked and limited per plan

---

## Phase 4: Billing Integration

**Priority:** MEDIUM
**Estimated Time:** 3-4 weeks
**Dependencies:** Phase 1, Phase 3

### Overview

Integrate Stripe for payment processing and subscription management.

### Features

#### 4.1 Stripe Integration

**New Dependencies:**
```bash
pip install stripe
```

**Configuration:**
```python
# backend/core/config.py
stripe_api_key: str = Field(validation_alias="STRIPE_API_KEY")
stripe_webhook_secret: str = Field(validation_alias="STRIPE_WEBHOOK_SECRET")
stripe_price_id_pro: str = Field(validation_alias="STRIPE_PRICE_ID_PRO")
```

#### 4.2 Checkout Flow

**New File: `backend/billing/service.py`**

```python
"""Stripe billing service."""

import stripe
from backend.core.config import get_settings

settings = get_settings()
stripe.api_key = settings.stripe_api_key


def create_checkout_session(user_id: UUID, plan_name: str, success_url: str, cancel_url: str):
    """Create Stripe checkout session."""
    session = stripe.checkout.Session.create(
        customer_email=user.email,
        payment_method_types=['card'],
        line_items=[{
            'price': settings.stripe_price_id_pro,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'user_id': str(user_id),
            'plan_name': plan_name,
        }
    )
    return session


def handle_webhook(payload: bytes, sig_header: str):
    """Handle Stripe webhook events."""
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = UUID(session['metadata']['user_id'])
        plan_name = session['metadata']['plan_name']

        # Activate subscription
        upgrade_user_plan(db, user_id, plan_name, duration_days=30)

    elif event['type'] == 'invoice.payment_failed':
        # Handle payment failure
        pass

    return {"status": "success"}
```

#### 4.3 API Endpoints

**New File: `backend/billing/api/routes.py`**

```python
@router.post("/create-checkout-session")
def create_checkout(
    plan: str,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe checkout session."""
    success_url = f"{settings.frontend_base_url}/subscription/success"
    cancel_url = f"{settings.frontend_base_url}/pricing"

    session = create_checkout_session(
        current_user.id, plan, success_url, cancel_url
    )

    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    return handle_webhook(payload, sig_header)
```

#### 4.4 Customer Portal

Add Stripe customer portal for managing subscriptions:

```python
@router.post("/customer-portal")
def customer_portal(
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """Create Stripe customer portal session."""
    subscription = get_user_subscription(db, current_user.id)

    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/account",
    )

    return {"portal_url": session.url}
```

### Success Criteria

- [ ] Stripe checkout creates subscription
- [ ] Webhook activates user subscription in database
- [ ] Customer portal allows subscription management
- [ ] Failed payments handled gracefully
- [ ] Subscription cancellation supported

---

## Phase 5: Advanced Features

**Priority:** LOW
**Estimated Time:** Ongoing

### Features (Pick as needed)

#### 5.1 Audit Logging

Track admin actions and sensitive operations.

**New Table: `audit_events`**

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,  -- 'user.suspended', 'plan.upgraded'
    resource_type VARCHAR(50),  -- 'user', 'subscription'
    resource_id UUID,
    metadata JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 5.2 User Impersonation

Allow admins to impersonate users for support.

```python
@router.post("/users/{user_id}/impersonate")
def impersonate_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Generate token to impersonate user."""
    # Create audit log
    create_audit_event(admin.id, 'user.impersonate', user_id)

    # Issue token with special claim
    token = jwt_service.issue_access_token(
        str(user_id),
        extra_claims={"impersonated_by": str(admin.id)}
    )

    return {"access_token": token}
```

#### 5.3 API Key Management

Allow users to generate API keys for programmatic access.

**New Table: `api_keys`**

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    prefix VARCHAR(20) NOT NULL,  -- For display (e.g., "sk_live_abc...")
    scopes JSONB,  -- {"read": true, "write": false}
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP
);
```

#### 5.4 Webhooks for Users

Allow users to register webhook URLs for events.

#### 5.5 Team/Organization Support

Multi-user organizations with shared plans.

#### 5.6 Usage Analytics Dashboard

Visualize usage trends for users and admins.

---

## Implementation Guidelines

### Development Process

1. **Feature Branch Strategy**
   - Create feature branch: `git checkout -b feature/subscription-system`
   - Never commit directly to `main`
   - One pull request per phase

2. **Database Migrations**
   - Always create migration: `alembic revision --autogenerate -m "description"`
   - Review generated SQL before applying
   - Test migrations on local DB first
   - Include rollback plan

3. **Testing Requirements**
   - Write unit tests BEFORE implementation (TDD)
   - Integration tests for API endpoints
   - Manual testing checklist
   - Load testing for rate limiting

4. **Code Review Checklist**
   - No changes to protected areas
   - All new code has tests
   - Migration tested locally
   - Documentation updated
   - API endpoints documented

5. **Deployment Steps**
   - Run migrations: `alembic upgrade head`
   - Restart services
   - Monitor logs for errors
   - Verify with smoke tests

### Coding Standards

**Database Models:**
```python
# Good: Use UUID primary keys
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# Good: Add indexes
__table_args__ = (Index('idx_user_email', 'email'),)

# Good: Use relationships
plan = relationship("SubscriptionPlan", back_populates="subscriptions")
```

**Service Functions:**
```python
# Good: Type hints and docstrings
def get_user_plan(db: Session, user_id: UUID) -> SubscriptionPlan:
    """Get subscription plan for user (defaults to free)."""
    pass

# Good: Error handling
if not user:
    raise ValueError(f"User {user_id} not found")
```

**API Endpoints:**
```python
# Good: Use Pydantic schemas
@router.post("/endpoint", response_model=ResponseSchema)
def endpoint(payload: RequestSchema):
    pass

# Good: Dependency injection
def endpoint(
    payload: RequestSchema,
    current_user: User = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    pass
```

### Rollback Plan

Each phase should have a rollback plan:

**Phase 1 Rollback:**
```bash
# Drop new tables
alembic downgrade -1

# Remove route registration
# (comment out in backend/app.py)
```

**Phase 2 Rollback:**
```bash
# Revoke admin flags
UPDATE users SET is_superadmin = FALSE WHERE is_superadmin = TRUE;

# Remove routes
```

---

## Testing Requirements

### Unit Tests

**Required for:**
- All service functions
- Business logic (quota checks, plan upgrades)
- Utility functions

**Example:**
```python
def test_get_user_plan_defaults_to_free():
    user = create_test_user()
    plan = get_user_plan(db, user.id)
    assert plan.name == 'free'

def test_check_quota_enforces_limit():
    user = create_test_user_with_plan('free')
    # Simulate usage at limit
    is_within, current, limit = check_quota(db, user.id, 'jobs')
    assert not is_within
```

### Integration Tests

**Required for:**
- API endpoints
- Database operations
- Rate limiting

**Example:**
```python
def test_create_job_respects_quota():
    client = TestClient(app)
    token = get_test_token()

    # Create jobs up to limit
    for _ in range(10):
        response = client.post("/jobs", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    # Next job should fail
    response = client.post("/jobs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 402
    assert "quota_exceeded" in response.json()["detail"]["error"]
```

### Manual Testing Checklist

**Phase 1:**
- [ ] Register new user → Has free plan
- [ ] Upgrade to pro → Rate limits increase
- [ ] Create jobs → Usage increments
- [ ] Exceed quota → Request blocked
- [ ] View `/v1/subscription/me` → Correct plan shown
- [ ] View `/v1/subscription/usage` → Correct usage shown

**Phase 2:**
- [ ] Non-admin cannot access `/v1/admin/*`
- [ ] Admin can list users
- [ ] Admin can suspend user → Login blocked
- [ ] Admin can clear rate limits → User can retry
- [ ] Admin can revoke sessions → User logged out
- [ ] View stats → Correct counts

---

## Summary

This roadmap provides a structured approach to implementing:

1. **Subscription system** with free/pro plans
2. **Admin backend** for user management
3. **Enhanced rate limiting** based on plans
4. **Billing integration** with Stripe
5. **Advanced features** as needed

**Key Principles:**
- ✅ Never touch working auth system
- ✅ Additive changes only (no breaking changes)
- ✅ Test everything before deploying
- ✅ Always have a rollback plan
- ✅ Document as you go

**Estimated Total Time:** 8-12 weeks for Phases 1-4

---

**Last Updated:** 2025-10-08
**Status:** Planning Phase
**Next Step:** Review and approve Phase 1 implementation plan
