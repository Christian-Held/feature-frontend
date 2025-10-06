# Authentication & Account Platform (Final Design)

This document finalizes the auth/account architecture tailored to the existing stack:

* **Backend:** FastAPI, Celery, Redis, SQLAlchemy, structlog (existing)
* **Workers/Queues:** Celery + Redis (existing)
* **Frontend:** React + TypeScript + Vite + Tailwind (existing)
* **Observability:** structlog; add OpenTelemetry
* **Current DB:** SQLite (dev). **Decision:** use PostgreSQL in prod for auth

The design avoids layout/style changes in the existing UI, adds new routes/screens, and keeps websocket/job features intact.

---

## 1. High-Level Architecture

**Frontend (React + TS + Vite)**

* Public routes: `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`, `/2fa/setup`, `/2fa/verify`.
* Authenticated routes: dashboard (existing) + `/account/security`, `/account/billing`, `/account/limits`, `/admin/*` (RBAC-gated).
* Global auth store handles JWT access/refresh, 401 intercept, token refresh, and logout.
* CAPTCHA widget: **Cloudflare Turnstile** (preferred) or **hCaptcha**. Required on registration; adaptive on login.

**Backend (FastAPI)**

* Services packaged as modules within the existing FastAPI app:

  * **Identity Service**: users, credentials, email verification, password reset.
  * **Auth Service**: login, JWT access/refresh (rotation), session revocation, 2FA (TOTP).
  * **IAM/RBAC**: roles, permissions, admin endpoints.
  * **Plans/Limits**: free/pro, monthly spend caps, “hard stop”.
  * **Notifications**: email (via Celery worker).
* **Celery workers**: email send, audit fan-out, cleanup jobs.
* **Redis**: broker + cache (CAPTCHA receipts, throttles, nonces, short-lived state).
* **DB**: PostgreSQL (prod), SQLite only for local dev. **Migrations via Alembic**.

**Security**

* Password hashing: **Argon2id** (argon2-cffi).
* JWT access (5–10 min) + rotating refresh (30 days). JWK (ES256/RS256) with `kid`.
* TOTP (RFC 6238) + recovery codes; enforce for admin.
* CSRF protection for cookie mode (optional). Default: Authorization Bearer tokens.
* Strict rate limiting (Redis), adaptive CAPTCHA, IP reputation hooks.

**Operations**

* Email: provider-agnostic (SMTP/SES/SendGrid). Outbound via Celery; retries + DLQ.
* Metrics (Prometheus) + tracing (OpenTelemetry). Structured logs via structlog.
* Feature flags to stage CAPTCHA & MFA.

---

## 2. Core User Flows

### A. Registration

1. `/register` form: email, password, optional name, CAPTCHA token.

2. `POST /v1/auth/register { email, password, captchaToken }`

   * Verify CAPTCHA (server-side).
   * If email exists & verified → `409 Email already registered`.
   * If exists but unverified:

     * If pending token < 24h → **resend** verification; respond 200: “Registration almost done — check your email. Link valid for 24h.”
     * If ≥24h expired → purge old token; issue new.
   * Create user: `status=UNVERIFIED`, `password_hash=Argon2id`.
   * Create verification token with 24h TTL (single-use), enqueue email.

3. Verification email:

   * Subject: “Confirm your email”
   * Link: `GET /v1/auth/verify-email?token=…`
   * Text: “Link valid for 24 hours. After that it expires and you can start over.”

4. Login before verification → `403`: “You must confirm your registration first. We’ve sent you an email.”

5. `POST /v1/auth/resend-verification` (rate-limited e.g., 3/day).

### B. Email Verification

* `GET /v1/auth/verify-email?token=…`

  * Validate signature, TTL, unused.
  * On success: set `email_verified_at`, `status=ACTIVE`, consume token; redirect to `/login?verified=1`.
  * On expiry: keep `UNVERIFIED`, free address for re-registration.

### C. Login with Adaptive CAPTCHA + 2FA

1. `/login`: email + password. Show CAPTCHA after N failed attempts or risky signals.

2. `POST /v1/auth/login`

   * If unverified → `403` with exact message above.
   * If CAPTCHA required but missing/invalid → `400 Captcha required`.
   * If wrong credentials → “Email or password is incorrect.”
   * On success:

     * If user has 2FA → `requires_2fa=true` and short-lived provisional token or challenge id.
     * Else issue access + refresh; set session record.

3. `POST /v1/auth/2fa/verify { otp, deviceName? }`

   * 5 wrong OTPs → temp lock (≈5 min) + force CAPTCHA next attempt.
   * Errors: “Invalid security code.”

### D. 2FA Setup & Recovery (Authenticated)

* `POST /v1/auth/2fa/enable-init` → returns secret (QR + manual) + `challengeId`.
* `POST /v1/auth/2fa/enable-complete { challengeId, otp }` → enables MFA; generate 10 recovery codes (display once).
* `POST /v1/auth/2fa/disable` → requires password + OTP.
* `POST /v1/auth/recovery-login { email, recoveryCode }` → rotates remaining codes.

### E. Forgot/Reset Password

* `POST /v1/auth/forgot-password { email }` → email with 1h reset token.
* `POST /v1/auth/reset-password { token, newPassword }`.
* Unverified users may reset password but must verify email to login.

### F. Plans, Quotas, Limits

* `/account/billing`: choose Free/Pro.
* `/account/limits`: monthly cap (USD), “hard stop” toggle, forecast usage.
* On cap reached: “Your monthly spending limit has been reached. Adjust your limit to continue.”

### G. Admin & Roles

* Seed initial admin from env (`ADMIN_EMAIL`, `ADMIN_PASSWORD`); force 2FA on first login.
* Roles: `ADMIN`, `USER`, optional `BILLING_ADMIN`, `SUPPORT`.
* Admin UI: manage users, roles, lock/unlock, resend email, reset 2FA, plan overrides, audit viewer.
* Unauthorized → “You don’t have permission to perform this action.”

---

## 3. Data Model (PostgreSQL)

**users**

* `id UUID PK`
* `email` (lowercased unique)
* `password_hash`
* `status` enum `UNVERIFIED|ACTIVE|DISABLED`
* `email_verified_at TIMESTAMP NULL`
* `mfa_enabled BOOL`
* `mfa_secret` (encrypted at rest)
* `recovery_codes` (encrypted JSON)
* `last_login_at`, `last_ip`
* `created_at`, `updated_at`

**email_verifications**

* `id UUID PK`, `user_id FK`
* `token_hash`
* `expires_at`, `used_at`, `created_at`

**password_resets**

* `id UUID PK`, `user_id FK`
* `token_hash`, `expires_at`, `used_at`

**roles**, **user_roles**

* Many-to-many; seed `ADMIN`, `USER`, etc.

**permissions**, **role_permissions** (optional now; keep simple RBAC initially)

**plans**, **user_plans**

* Current plan, `renews_at`, `status`

**spend_limits**

* `user_id`, `monthly_cap_usd`, `hard_stop BOOL`

**sessions**

* `id UUID`, `user_id`, `refresh_token_hash`, `ua`, `ip`
* `expires_at`, `rotated_at`, `revoked_at`

**audit_logs**

* `id`, `actor_user_id`, `action`, `target_type`, `target_id`, `ip`, `ua`, `metadata JSON`, `created_at`

**login_attempts** (or only Redis)

* For throttling/adaptive CAPTCHA (Redis preferred)

**captcha_receipts** (optional persistent copy for compliance; Redis by default)

**Migrations:** Alembic scripts; seed admin+roles.

---

## 4. API Surface (FastAPI)

**Auth**

* `POST /v1/auth/register`
* `POST /v1/auth/resend-verification`
* `GET /v1/auth/verify-email`
* `POST /v1/auth/login`
* `POST /v1/auth/2fa/verify`
* `POST /v1/auth/logout`
* `POST /v1/auth/refresh` (rotate; revoke previous)
* `POST /v1/auth/forgot-password`
* `POST /v1/auth/reset-password`
* `GET /v1/auth/me` (profile, roles, plan, limits)

**2FA**

* `POST /v1/auth/2fa/enable-init`
* `POST /v1/auth/2fa/enable-complete`
* `POST /v1/auth/2fa/disable`
* `POST /v1/auth/recovery-login`

**Plans & Limits**

* `GET/POST /v1/account/plan`
* `GET/POST /v1/account/limits`

**Admin**

* `GET /v1/admin/users`
* `POST /v1/admin/users/:id/roles`
* `POST /v1/admin/users/:id/lock` | `unlock`
* `POST /v1/admin/users/:id/reset-2fa`
* `GET /v1/admin/audit-logs`

**Notes**

* All write endpoints: enforce RBAC; rate-limit sensitive ones.
* If cookie auth is later enabled: CSRF tokens for write endpoints.

---

## 5. Frontend Requirements

* **No global layout/style changes**; add pages with existing theme/components.
* Exact error copy:

  * Unverified: “You must confirm your registration first. We’ve sent you an email.”
  * OTP invalid: “Invalid security code.”
  * CAPTCHA required: “Captcha required.”
  * Unauthorized: “You don’t have permission to perform this action.”
  * Spending cap reached: “Your monthly spending limit has been reached. Adjust your limit to continue.”
* Registration: password strength meter; CAPTCHA required.
* Login: adaptive CAPTCHA after failures/risk.
* 2FA: QR + manual key; one-time display of recovery codes (download/copy).
* Account/Security: change password, enable/disable 2FA, list sessions/devices, “sign out others”.
* Billing/Limits: plan switch, cap input, forecast, hard-stop toggle.
* Token handling: keep access token in memory; refresh token in httpOnly cookie or secure storage per chosen mode; automatic refresh once on 401, then logout.
* Show “email not verified” banner if backend states unverified.

---

## 6. Security Controls

* **Argon2id** with strong params; optional pepper via env (KMS/Vault).
* **JWT** (ES256/RS256): short access; rotating refresh; per-session storage with hash; revoke on logout/rotation.
* Session fixation prevention; optional bind refresh to IP/UA.
* CAPTCHA server-side verification; store minimal receipt.
* Rate limits (Redis): register, login, resend, forgot/reset, 2FA verify.
* Progressive lockouts: e.g., 5/15/60 min; email notifications for lock/unknown device.
* CSP, HSTS, SameSite cookies (if cookie mode), secure headers via FastAPI middleware.
* GDPR: deletion/export flows (backlog item), consent tracking (backlog).
* Secrets via env; never log secrets; structured logs with redaction.

---

## 7. Ops & Observability

* **Metrics (Prometheus):** login success/fail, 2FA adoption, resend counts, lockouts, email latency, refresh success rate.
* **Tracing (OTel):** gateway → FastAPI → Celery → SMTP.
* **Alerts:** spikes in 401/403, high bounce rates, token refresh errors, queue backlog.
* **Runbooks:** email outage (queue & replay), CAPTCHA outage (grace users with tighter rate limits), key rotation procedure.

---

## 8. Integration with Auto Dev Orchestrator

* New auth endpoints live under `/v1/*` alongside existing `/api/*`; no breaking changes to orchestrator routes, websockets, or job flows.
* Admin role can access orchestrator settings; existing settings UI gated by RBAC.
* Keep PR automation unchanged; add audit logs for auth/admin actions.
* Background jobs (emails/cleanup) use existing Celery/Redis setup.

---

## 9. Implementation Plan (Milestones)

**M1 – Foundations**

* Add Postgres support; Alembic migrations for core tables; seed admin.
* JWT keys & rotation; Argon2id; Redis integration; rate limiter middleware.

**M2 – Registration & Verification**

* Register, resend, verify endpoints.
* Email templates + Celery tasks.
* Frontend register/verify pages + exact copy.

**M3 – Login, Sessions, 2FA**

* Login, refresh rotation, logout, session store.
* TOTP enable/verify/disable, recovery codes.
* Frontend login, 2FA setup/verify, security page.

**M4 – Plans & Limits**

* Plan/limit endpoints; enforcement hook; UI pages.

**M5 – Admin & Auditing**

* Admin endpoints/UI, audit log viewer, user management.

**M6 – Hardening & SRE**

* OTel tracing, Prometheus metrics, alerts, runbooks, pen-test fixes.

---

## 10. Technology Choices (Final)

* **FastAPI** (stay in Python stack) for all auth APIs.
* **SQLAlchemy + Alembic** for ORM/migrations.
* **PostgreSQL** production DB.
* **Redis** for broker/cache/rate limits.
* **Celery** for async email and cleanup.
* **argon2-cffi** for password hashing.
* **PyJWT / python-jose** for JWT + JWK rotation.
* **pyotp/qrcode** for TOTP + QR.
* **Cloudflare Turnstile** (preferred) or **hCaptcha** for CAPTCHA.
* **smtplib/aiosmtplib** or provider SDK (SES/SendGrid) for email.
* **OpenTelemetry** for tracing; **Prometheus** client for metrics.

---

## 11. Exact UX Copy (English)

* Registration submitted: “Registration almost done — check your email. The link is valid for 24 hours.”
* Login before verification: “You must confirm your registration first. We’ve sent you an email.”
* Invalid OTP: “Invalid security code.”
* CAPTCHA required: “Captcha required.”
* Unauthorized: “You don’t have permission to perform this action.”
* Cap reached: “Your monthly spending limit has been reached. Adjust your limit to continue.”

---

## 12. Backlog & Future

* WebAuthn (passkeys) as optional second factor.
* Org/teams, SSO (OIDC/SAML).
* Consent & GDPR self-service.
* SMS/Push notifications (Notification Service expansion).

---

**Decision Summary:** Implement the auth platform **within the current FastAPI/Celery/Redis/React stack**, using PostgreSQL in production, Argon2id for hashing, JWT with refresh rotation, TOTP-based 2FA, Cloudflare Turnstile CAPTCHA, and RBAC with an admin bootstrap. This preserves existing architecture, minimizes operational overhead, and is production-ready with clear milestones.
