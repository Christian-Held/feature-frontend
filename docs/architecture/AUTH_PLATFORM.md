# Authentication & Account Platform Architecture

This document summarizes the target end-to-end architecture for the authentication, authorization, and account experience. It captures backend service boundaries, frontend flows, data structures, and operational guardrails required to deliver the experience.

## 1. High-Level Architecture

- **Frontend (React)**
  - Public routes: `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`, `/2fa/setup`, `/2fa/verify`.
  - Authenticated routes: dashboard plus account pages (`/account/security`, `/account/billing`, `/account/limits`).
  - Shared auth SDK responsible for backend calls, token refresh, and handling `401/403` responses.
  - CAPTCHA widget (Turnstile or hCaptcha) required on registration and shown adaptively on login.
- **Backend/API** (microservice-friendly; Spring Boot preferred, FastAPI acceptable when mirroring boundaries)
  - Identity Service (users, credentials, email verification, password reset).
  - Auth Service (sessions, JWTs, refresh rotation, 2FA/TOTP/WebAuthn).
  - Notification Service (email now, SMS/Push later).
  - Admin / IAM Service (roles, permissions, policy enforcement).
  - Billing/Plans Service (free/pro tiers, quotas/limits).
- **Edge/API Gateway** providing rate limiting, CORS, request signing, and WAF policies.
- **Supporting infrastructure**
  - Message broker (RabbitMQ or Redis Streams) for async email delivery and audit log fan-out.
  - Cache (Redis) storing nonces, short-lived state, CAPTCHA receipts, and login throttles.
- **Data storage**
  - PostgreSQL primary relational store; S3/Blob storage for audit exports and backups.
  - Database migrations managed through Liquibase or Flyway.
- **Security posture**
  - Password hashing via Argon2id.
  - JWT access tokens (5–10 minute TTL) plus rotating refresh tokens (30-day TTL, revocable).
  - TOTP (RFC 6238) with recovery codes; WebAuthn is optional for future expansion.
  - CAPTCHA server-side verification, device/session management, IP reputation, and adaptive challenges.
  - Comprehensive audit logging across the stack.

## 2. Core User Flows

### A. Registration

1. User opens `/register` with fields for email, password, optional name, and CAPTCHA.
2. Frontend validates input, collects CAPTCHA token, and calls `POST /v1/auth/register { email, password, captchaToken }`.
3. Backend actions:
   - Verify CAPTCHA receipt.
   - If email exists and is verified → `409 Email already registered`.
   - If email exists but is unverified:
     - If a previous verification exists within 24h → resend link and return 200 with message: “Registrierung fast abgeschlossen — bitte bestätige deine E-Mail. Der Link ist 24 Stunden gültig.”
     - If ≥24h expired → purge old token and issue a new one.
   - Create user with `status=UNVERIFIED`, hash password (Argon2id), generate verification token (24h TTL, single-use), enqueue email.
4. Email content:
   - Subject “Bitte bestätige deine E-Mail”.
   - Body includes `GET /v1/auth/verify-email?token=…` and the statement “Dieser Link ist 24 Stunden gültig. Danach verfällt die Registrierung automatisch.”
5. Login attempt prior to verification returns `403` with message: “Du musst die Registrierung erst noch bestätigen. Wir haben dir eine E-Mail geschickt.”
6. Provide `POST /v1/auth/resend-verification` with rate-limit (e.g., 3/day).

### B. Email Verification

- `GET /v1/auth/verify-email?token=…` validates signature, TTL, and usage.
- Expired tokens mark the attempt as expired, keep account `UNVERIFIED`, and free the email for a new registration.
- Successful verification sets `email_verified_at`, `status=ACTIVE`, consumes the token, and redirects frontend to `/login?verified=1`.

### C. Login with CAPTCHA + 2FA

1. User submits email and password on `/login`; CAPTCHA displayed adaptively after failed attempts, risky IPs, or velocity triggers.
2. `POST /v1/auth/login` validates credentials and CAPTCHA requirements.
   - Missing verification → `403` with “Du musst die Registrierung erst noch bestätigen. Wir haben dir eine E-Mail geschickt.”
   - CAPTCHA missing/invalid when required → `400` “Captcha erforderlich.”
   - Incorrect password → “Benutzername oder Passwort ist falsch.”
   - Account lock after repeated failures → “Konto vorübergehend gesperrt. Bitte versuche es in einigen Minuten erneut.”
3. Successful password authentication without 2FA issues short-lived access token and rotating refresh token.
4. For TOTP-enabled accounts `requires_2fa=true` is returned; frontend routes to `/2fa/verify` and calls `POST /v1/auth/2fa/verify` with OTP and optional device name.
5. Five incorrect OTP attempts trigger a temporary lock (≈5 minutes) and force CAPTCHA on the next attempt.
6. OTP validation errors return “Der eingegebene Sicherheitscode ist ungültig.”

### D. 2FA Setup & Recovery

POST /v1/auth/2fa/enable-init
→ returns secret (QR + manual) + challengeId.

POST /v1/auth/2fa/enable-complete { challengeId, otp }
→ enables MFA; generate 10 recovery codes (display once).

POST /v1/auth/2fa/disable { password, otp }
→ disables MFA.

POST /v1/auth/recovery-login { email, password, recoveryCode, challengeId? }
→ validates password first, verifies recovery code (single use), rotates remaining codes,
   and issues new access/refresh tokens.

### E. Forgot & Reset Password

- `POST /v1/auth/forgot-password { email }` sends reset link with 1h TTL.
- `POST /v1/auth/reset-password { token, newPassword }` performs reset; unverified accounts can reset but must verify email before login.

### F. Plans, Quotas, and Limits

- `/account/billing` and `/account/limits` provide plan management (Free/Pro), spend cap per month (USD), forecast usage, and “hard stop” toggle.
- Admin defines defaults and hard caps; reaching the cap surfaces: “Dein monatliches Ausgabenlimit wurde erreicht. Passe dein Limit an, um fortzufahren.”

### G. Admin & Roles (RBAC)

- Initial admin seeded on first migration (env-driven).
- Roles: `ADMIN`, `USER`, optional `BILLING_ADMIN`, `SUPPORT` mapped to granular permissions.
- Admin UI covers user management (invite, deactivate, reset 2FA, role assignment), plan overrides, audit viewer, email resend, lock/unlock.
- Unauthorized response message: “Keine Berechtigung für diese Aktion.”

## 3. Data Model (PostgreSQL)

| Table | Key Columns & Notes |
| --- | --- |
| `users` | `id (uuid)`, `email` (lowercased unique; nullable until verified strategy), `email_verified_at`, `status` (`ACTIVE|UNVERIFIED|DISABLED`), `password_hash`, `mfa_enabled`, `mfa_secret` (encrypted), `recovery_codes` (encrypted JSON), timestamps (`created_at`, `updated_at`), `last_login_at`, `last_ip`. |
| `email_verifications` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at`, `created_at`. |
| `password_resets` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at`. |
| `roles` / `user_roles` | Role definitions and assignments. |
| `permissions` / `role_permissions` | Granular permission model mapped to roles. |
| `plans` / `user_plans` | Plan catalog and per-user subscription state (`renews_at`, `status`). |
| `spend_limits` | `user_id`, `monthly_cap_usd`, `hard_stop (bool)`. |
| `sessions` | `id`, `user_id`, `refresh_token_hash`, `expires_at`, `rotated_at`, `ua`, `ip`, `revoked_at`. |
| `audit_logs` | `id`, `actor_user_id`, `action`, `target_type`, `target_id`, `ip`, `ua`, `metadata JSON`, `created_at`. |
| `captcha_receipts` (cache preferred) | Optional persistent records for compliance. |
| `login_attempts` (or Redis keys) | Supports throttling, adaptive challenges, and lockouts. |

## 4. API Surface

### Auth Endpoints

- `POST /v1/auth/register`
- `POST /v1/auth/resend-verification`
- `GET /v1/auth/verify-email?token=…`
- `POST /v1/auth/login`
- `POST /v1/auth/2fa/verify`
- `POST /v1/auth/logout`
- `POST /v1/auth/refresh` (rotate + revoke previous refresh token)
- `POST /v1/auth/forgot-password`
- `POST /v1/auth/reset-password`
- `GET /v1/auth/me` (profile, roles, plan, limits)

### 2FA Endpoints

- `POST /v1/auth/2fa/enable-init`
- `POST /v1/auth/2fa/enable-complete`
- `POST /v1/auth/2fa/disable`
- `POST /v1/auth/recovery-login`

### Plans & Limits

- `GET /v1/account/plan`, `POST /v1/account/plan`
- `GET /v1/account/limits`, `POST /v1/account/limits`

### Admin

- `GET /v1/admin/users`, `POST /v1/admin/users/:id/roles`
- `POST /v1/admin/users/:id/lock` | `unlock`
- `POST /v1/admin/users/:id/reset-2fa`
- `GET /v1/admin/audit-logs`

_All write endpoints require CSRF protection (for cookie-based auth) and RBAC enforcement._

## 5. Frontend Application Requirements

- Maintain existing layout and styling while adding screens for login, registration, verification outcomes, 2FA setup/verify, account security, billing/plan selection, and usage limits.
- Implement password strength meter on registration and exact error texts as specified.
- Surface resend verification link from login when backend responds with the unverified message.
- Provide QR and manual code during 2FA setup and present recovery codes once for download.
- Account security page includes password change, 2FA enable/disable, session/device list, and “sign out others”.
- Billing/plan page presents plan comparison, spend cap input, usage forecast, and hard-stop toggle.
- Global auth store manages access/refresh tokens, automatic refresh on `401`, retries once, then logs out.
- Show “email not verified” banner if a user somehow bypasses verification enforcement.

## 6. Security & Compliance Controls

- Argon2id hashing with strong parameters; consider pepper from HSM/KMS.
- JWTs signed using JWS (ES256/RS256) with `kid` rotation, short access token TTL (5–10 minutes), refresh tokens (~30 days) rotated on use and revocable on logout.
- Prevent session fixation; optionally bind refresh tokens to IP/UA.
- Verify CAPTCHA server-side, storing minimal receipts for audit without PII.
- Enforce rate limits on registration, login, resend, and forgot-password flows.
- Progressive lockouts (e.g., 5/15/60 minutes) with email notifications for lock events and new device logins.
- Audit logging for auth events, admin actions, plan changes; redact secrets and sensitive values.
- Support GDPR workflows: email erasure, data export, marketing consent tracking.
- Manage secrets via Vault/KMS, configure via environment variables, and avoid logging secrets.
- Apply CSP, HSTS, and SameSite cookies (if cookies are used).
- Verification tokens must expire after 24h; on expiry, allow re-registration and free the email address.

## 7. Operations, Observability & SRE

- **Metrics (Prometheus):** login success/failure, 2FA adoption, resend counts, lockouts, email delivery latencies, token refresh rates.
- **Tracing (OpenTelemetry):** propagate spans across gateway → services → SMTP.
- **Alerts:** spikes in `401/403`, high email bounce rates, CAPTCHA failures, token refresh anomalies.
- **Runbooks:** address email outages (queue & replay), CAPTCHA outages (grace users with tighter rate limits).
- **Feature flags:** staged rollout (register CAPTCHA, login CAPTCHA, 2FA requirements per role/tenant).

## 8. Initial Admin Bootstrap

- First migration seeds role/permission sets and creates an admin user (`ADMIN_EMAIL`, `ADMIN_PASSWORD` env values).
- Seeded admin is marked as email-verified and must enroll 2FA on first login.
- Subsequent admin invites managed via Admin UI; all admin logins must enforce 2FA.

