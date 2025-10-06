# Authentication & Account Platform — Final Enterprise Design

Dieses Dokument ist **die einzige maßgebliche Spezifikation**. Keine Alternativen, keine „optional“-Pfade. Implementiere exakt so.

---

## 0. Ziele und Nicht-Ziele

**Ziele**

* Sichere Benutzer-Identität, Sessions, RBAC, Pläne/Limits, Admin.
* Deterministischer Codepfad für Auto-Dev-Orchestrator.
* Enterprise-fähig: Security, Compliance, Observability, Resilienz, Skalierung.

**Nicht-Ziele**

* Kein SSO/OIDC/SAML, keine Passkeys in v1.
* Keine Multi-DB, kein anderes CAPTCHA, kein anderer Stack.

---

## 1. Architekturübersicht

**Stack**

* Backend: FastAPI (Python 3.11), Celery, Redis, SQLAlchemy, structlog
* Frontend: React + TypeScript + Vite + Tailwind
* Datenbank: PostgreSQL 15+ (Prod), SQLite nur lokale Dev
* Migrations: Alembic
* Tracing/Metrics: OpenTelemetry, Prometheus
* Logs: structlog (JSON)
* CAPTCHA: Cloudflare Turnstile
* E-Mail: SMTP/SES/SendGrid via Celery

**Services im FastAPI-Monolith**

* Identity: User, Credentials, E-Mail-Verifikation, Password Reset
* Auth: Login, JWT Access/Refresh Rotation, Sessions, TOTP
* IAM/RBAC: Rollen, Berechtigungen, Admin-Endpunkte
* Plans/Limits: Free/Pro, Monatsbudget, Hard-Stop
* Notifications: E-Mail-Versand, Vorlagen

**Infra**

* Redis: Celery-Broker + Cache (Throttles, Nonces, CAPTCHA-Receipts)
* Object Storage (S3-kompatibel): Backups, optionale Audit-Exports
* Reverse Proxy/TLS: Caddy/Traefik oder NGINX (TLS 1.2/1.3, HSTS)

**Frontend Routen**

* Public: `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password`, `/2fa/setup`, `/2fa/verify`
* Authenticated: Dashboard, `/account/security`, `/account/billing`, `/account/limits`, `/admin/*`

---

## 2. Sicherheits-Grundsätze

* Passwort-Hash: **Argon2id** mit Params: `time_cost=3`, `memory_cost=64*1024 KB`, `parallelism=2`, `hash_len=32`, `salt_len=16`
* JWT: ES256 (P-256). Access TTL **7 min**. Refresh TTL **30 Tage**. **Rotation auf jede Nutzung**. JWKs mit `kid`, Key-Roll alle **90 Tage**.
* TOTP (RFC 6238) 30s Intervall, 6 Stellen, Drift ±1. Admins **müssen** TOTP aktivieren.
* Rate Limits (Redis):

  * Register: 5/Std/IP
  * Login: 10/15min/IP + 5/15min/Account
  * Resend Verification: 3/Tag/Account
  * Forgot Password: 3/Std/Account
  * 2FA Verify: 10/15min/Account
* Adaptive CAPTCHA bei Risiko oder nach Fehlschlägen.
* Session Fixation Prevention, Refresh an UA und /24-IP binden.
* CSRF-Schutz nur bei Cookie-Modus. Standard: Bearer im `Authorization`.
* Secrets niemals loggen. Selektive Redaction in structlog.

---

## 3. Datenmodell (PostgreSQL)

**users**

* `id UUID PK`
* `email CITEXT UNIQUE NOT NULL`
* `password_hash TEXT NOT NULL`
* `status ENUM('UNVERIFIED','ACTIVE','DISABLED') NOT NULL`
* `email_verified_at TIMESTAMPTZ NULL`
* `mfa_enabled BOOL NOT NULL DEFAULT false`
* `mfa_secret BYTEA NULL` (verschlüsselt)
* `recovery_codes BYTEA NULL` (verschlüsselt JSON)
* `last_login_at TIMESTAMPTZ NULL`, `last_ip INET NULL`
* `created_at`, `updated_at` (TIMESTAMPTZ, default now)

**email_verifications**

* `id UUID PK`, `user_id UUID FK`
* `token_hash BYTEA NOT NULL`
* `expires_at TIMESTAMPTZ NOT NULL`, `used_at TIMESTAMPTZ NULL`
* `created_at TIMESTAMPTZ NOT NULL`

**password_resets**

* `id UUID PK`, `user_id UUID FK`
* `token_hash BYTEA NOT NULL`
* `expires_at TIMESTAMPTZ NOT NULL`, `used_at TIMESTAMPTZ NULL`

**roles**, **user_roles**

* Rollen: `ADMIN`, `USER`, optional intern `BILLING_ADMIN`, `SUPPORT`
* `user_roles(user_id, role_id)` UNIQUE

**permissions**, **role_permissions**

* V1 rudimentär. Mapping hinterlegt, API strikt auf Rollen.

**plans**, **user_plans**

* Plan: `FREE`, `PRO`
* `renews_at TIMESTAMPTZ`, `status ENUM('ACTIVE','CANCELLED','PAST_DUE')`

**spend_limits**

* `user_id`, `monthly_cap_usd NUMERIC(12,2)`, `hard_stop BOOL`

**sessions**

* `id UUID PK`, `user_id`
* `refresh_token_hash BYTEA`
* `ua TEXT`, `ip INET`
* `expires_at`, `rotated_at`, `revoked_at` (TIMESTAMPTZ)

**audit_logs**

* `id UUID PK`, `actor_user_id UUID NULL`
* `action TEXT`, `target_type TEXT`, `target_id TEXT`
* `ip INET`, `ua TEXT`, `metadata JSONB`, `created_at TIMESTAMPTZ`

**login_attempts** (Redis-Keys), **captcha_receipts** (Redis)

* Persistenz optional, Default Cache.

**Kryptospeicher**

* `mfa_secret` und `recovery_codes` mit AES-GCM appl.-seitig verschlüsseln. Key via KMS/Env.

---

## 4. API (FastAPI, `/v1/*`)

**Auth**

* `POST /auth/register` `{ email, password, captchaToken }`
* `POST /auth/resend-verification`
* `GET /auth/verify-email?token=...`
* `POST /auth/login` `{ email, password, captchaToken? }`
* `POST /auth/2fa/verify` `{ otp, deviceName? }`
* `POST /auth/logout`
* `POST /auth/refresh`
* `POST /auth/forgot-password` `{ email }`
* `POST /auth/reset-password` `{ token, newPassword }`
* `GET /auth/me`

**2FA**

* `POST /auth/2fa/enable-init`
* `POST /auth/2fa/enable-complete`
* `POST /auth/2fa/disable`
* `POST /auth/recovery-login` `{ email, recoveryCode }`

**Plans & Limits**

* `GET /account/plan`, `POST /account/plan`
* `GET /account/limits`, `POST /account/limits`

**Admin (RBAC: ADMIN)**

* `GET /admin/users` (Filter/Paging)
* `POST /admin/users/:id/roles`
* `POST /admin/users/:id/lock`
* `POST /admin/users/:id/unlock`
* `POST /admin/users/:id/reset-2fa`
* `GET /admin/audit-logs` (Filter/Paging)

**Fehlertexte (exakt)**

* Unverified: “You must confirm your registration first. We’ve sent you an email.”
* Invalid OTP: “Invalid security code.”
* CAPTCHA required: “Captcha required.”
* Unauthorized: “You don’t have permission to perform this action.”
* Cap reached: “Your monthly spending limit has been reached. Adjust your limit to continue.”
* Wrong creds: “Email or password is incorrect.”

**HTTP**

* 200/201/204 bei Erfolg, 400/401/403/409/429/500 deterministisch.
* Idempotency: Resend/Forgot via request key throttlen.

---

## 5. User Flows

**Registration**

1. `/register` sammelt `email`, `password`, CAPTCHA.
2. `POST /auth/register`
3. Server: Turnstile prüfen, E-Mail-Collision, `UNVERIFIED` User anlegen, Verifikations-Token (24h, single use) generieren, E-Mail enqueuen.
4. Response 200: “Registration almost done — check your email. The link is valid for 24 hours.”

**E-Mail-Verifikation**

* `GET /auth/verify-email?token=...` prüft Signatur/TTL/Unused.
* Erfolg → `email_verified_at` setzen, `ACTIVE`, Token konsumieren, Redirect `/login?verified=1`.
* Expired → bleibt `UNVERIFIED`, Adresse für Neureg erlaubt.

**Login + Adaptive CAPTCHA + 2FA**

* `/login` zeigt CAPTCHA nach Limits/Risiko.
* `POST /auth/login`:

  * Unverified → 403 mit Text oben.
  * Fehlerhafte CAPTCHA wenn gefordert → 400.
  * Falsche Daten → generischer Fehlertext.
  * Erfolg:

    * Ohne 2FA → Access + Refresh ausgeben und Session recorden.
    * Mit 2FA → `requires_2fa=true` zurückgeben, Frontend ruft `/auth/2fa/verify`.
* `POST /auth/2fa/verify`: 5 Fehlversuche → 5-Min-Sperre + CAPTCHA erzwingen.

**2FA Setup/Recovery**

* `enable-init` liefert QR+manuellen Code+`challengeId`.
* `enable-complete` validiert `otp`, setzt `mfa_enabled=true`, generiert 10 Recovery Codes (einmalig anzeigen/download).
* `disable` verlangt Passwort + OTP.
* `recovery-login` nutzt validen Code und rotiert Rest.

**Forgot/Reset**

* `forgot-password` sendet 1h Reset-Token.
* `reset-password` setzt neues PW; Login erst nach Verifikation.

**Plans/Limits**

* `/account/billing` wählt `FREE`/`PRO`.
* `/account/limits` setzt Monats-Cap USD und Hard-Stop.
* Bei Cap: HTTP 402 analog Text oben.

**Admin**

* Bootstrap Admin aus ENV, TOTP bei erstem Login erzwingen.
* Rollen pflegen, Lock/Unlock, Reset 2FA, Audit Viewer.

---

## 6. Frontend Anforderungen

* Keine globalen Layoutänderungen.
* Auth Store: Access im Speicher, Refresh in httpOnly Cookie **oder** in sicherem Storage je Betriebsmodus. **Standard: Bearer+Local Storage für Access, Refresh als httpOnly-Cookie**.
* 401-Interceptor: einmaliger Silent-Refresh, danach Logout.
* Password Strength Meter (z. B. zxcvbn).
* 2FA-Setup mit QR, Recovery-Codes nur einmal anzeigen + Download.
* Security-Seite: Passwort ändern, 2FA togglen, Sessions anzeigen, „sign out others“.
* Billing/Limits: Plan-Switch, Cap-Eingabe, Forecast, Hard-Stop.

---

## 7. Betrieb & Observability

**Metriken (Prometheus)**

* Auth: `login_success_total`, `login_failure_total`, `totp_failure_total`, `captcha_challenges_total`, `refresh_success_total`, `lockouts_total`
* Email: `email_enqueued_total`, `email_send_latency_ms`, `email_failed_total`
* Rate Limit Hits: `rate_limit_block_total`
* Plans/Limits: `cap_reached_total`

**Tracing (OTel)**

* End-to-End: Frontend → FastAPI → Celery → SMTP. Kontextpropagation aktiv.

**Logs**

* JSON, PII-Redaction für E-Mail, IP teilweise maskiert, keine Tokens/Secrets.

**Alerts**

* Spikes 401/403/429
* Email Queue Backlog > X
* Refresh-Fehlerquote > Y%
* CAPTCHA Fehlerquote > Z%

**Runbooks**

* E-Mail Outage: Queue füllen, später Replay.
* CAPTCHA Outage: Fail-open nur nach explizitem Feature Flag, gleichzeitig Limits verschärfen.
* Key Rotation: `kid` neu ausrollen, Refresh parallel akzeptieren bis T+24h.

**SLO/SLA**

* Auth API p95 Latenz < 150 ms
* Login Fehlerquote < 1%
* E-Mail Zustell-Start < 30 s p95
* RTO 1h, RPO 15 min

**Backups**

* Postgres: PITR fähig, tägliche Full, 15-min WAL Upload, 30 Tage Retention.
* Alembic Versions unter Versionskontrolle.

---

## 8. Compliance & Datenschutz (GDPR)

* Rechtsgrundlagen: Vertragserfüllung (Art. 6(1)(b)) für Auth; berechtigtes Interesse für Sicherheit.
* Datenminimierung: nur erforderliche PII speichern.
* Aufbewahrung: Accounts löschbar. Löschung: Soft-Delete + 30 Tage Quarantäne, danach Hard-Delete; Audit-Logs 365 Tage.
* Betroffenenrechte: Export (JSON), Löschung, Berichtigung.
* Auftragsverarbeitung: DPA mit E-Mail-Provider/Cloud.
* DPIA für Auth-Risiken dokumentieren.
* Cookies: nur technisch notwendige (Refresh httpOnly).
* Internationaler Transfer: Standardvertragsklauseln falls nötig.

---

## 9. Integrationspunkte Auto-Dev Orchestrator

* Neue Endpunkte unter `/v1/*`, bestehende `/api/*` unverändert.
* Admin RBAC schützt Orchestrator-Settings.
* Pull-Request-Automationen unverändert; neue Audit-Events für Admin-Aktionen.

---

## 10. Deploy & Environments

**Envs**: `dev`, `staging`, `prod`. Gleiche Artefakte, andere Konfig.

**Environment Variables (Muss)**

* `DB_URL` (Postgres), `REDIS_URL`
* `JWT_JWK_CURRENT` (ES256), `JWT_JWK_NEXT` (für Rotation)
* `ARGON2_TIME`, `ARGON2_MEMORY`, `ARGON2_PARALLELISM`
* `TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`
* `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `EMAIL_FROM`
* `ADMIN_EMAIL`, `ADMIN_PASSWORD`
* `ENCRYPTION_KEY` (AES-GCM für mfa/recovery)
* `OTEL_EXPORTER_OTLP_ENDPOINT`, `PROMETHEUS_SCRAPE=1`

**Startup-Order**

1. DB Migrations (Alembic)
2. FastAPI App
3. Celery Worker/Beat
4. Proxy/TLS
5. Metrics/Tracing Exporter

**CORS/CSP**

* CORS: Origins fest whitelisten.
* CSP: `default-src 'self'`; `script-src 'self' https://challenges.cloudflare.com`; `connect-src 'self' https://api.cloudflare.com`; `frame-src https://challenges.cloudflare.com`; `img-src 'self' data:`

---

## 11. Teststrategie

* Unit: Hashing, JWT, Token Rotation, Rate Limit
* Integration: Register→Verify→Login→2FA→Refresh→Logout
* Security Tests: Timing-Safe Vergleiche, Replay-Prevention, Locked Account
* E2E: Cypress/Playwright Flows für FE
* Load: Login 200 RPS, p95 < 150 ms
* Chaos: Redis/SMTP/DB kurzzeitig unzugänglich, korrekte Degradierung

---

## 12. Milestones (Tasks für Codex)

**M1 – Foundations**

* Postgres + Alembic, Seed Admin, Redis Integration, Argon2id, JWT/JWK Rotation, Rate-Limiter Middleware

**M2 – Registration & Verification**

* Endpunkte, E-Mail Templates, FE Seiten, Turnstile Integration

**M3 – Login, Sessions, 2FA**

* Login/Refresh/Logout, Session Store, TOTP + Recovery Codes, FE Security-Seiten

**M4 – Plans & Limits**

* Endpunkte, Enforcement Hook, FE Pages, Cap-Banner

**M5 – Admin & Auditing**

* Admin APIs/UI, Audit Viewer, Role Management

**M6 – Hardening & SRE**

* OTel, Prometheus, Alerts, Runbooks, Key-Rotation Pipeline, Pen-Test Fixes

---

## 13. E-Mail-Vorlagen

* Verify: Betreff “Confirm your email”, Link 24h gültig.
* Reset: Betreff “Reset your password”, Link 1h gültig.
* Lockout: “Account temporarily locked due to multiple failed attempts.”
* New Device: “New sign-in detected.”

Alle Plain-Text + einfache HTML, keine Tracking-Pixel.

---

## 14. Edge-Cases & Fail-Szenarien

* Doppelregistrierung unverifizierter E-Mail: Resend statt Fehler.
* Verifikations-Token Reuse: One-time, nach Nutzung ungültig.
* Refresh Theft: Rotation + Revoke auf Nutzung des alten Tokens, alle Sessions des Users invalidieren.
* Clock Skew: ±2min Toleranz bei TOTP/JWT.
* IP-Wechsel Mobil: Refresh Bindung /24, nicht vollständige IP.

---

## 15. Performance & Skalierung

* DB Indizes: `users.email`, `sessions.user_id`, `audit_logs.created_at`, `user_roles.user_id`
* Caching: Login Throttles/CAPTCHA in Redis, keine PII im Cache.
* Celery Concurrency: CPU-Kerne x2, Backoff-Retry für SMTP.

---

## 16. Passwort- und Validierungsregeln

* Passwort min 10 Zeichen, Check gegen häufige Leaks (lokale Liste).
* E-Mail normalisieren lower-case, Trim.
* Gerät/UA Länge begrenzen, Validierung serverseitig.

---

## 17. Konstante Texte (FE/BE identisch)

* „Registration almost done — check your email. The link is valid for 24 hours.“
* „You must confirm your registration first. We’ve sent you an email.“
* „Invalid security code.“
* „Captcha required.“
* „You don’t have permission to perform this action.“
* „Your monthly spending limit has been reached. Adjust your limit to continue.“
* „Email or password is incorrect.“

---

## 18. Unveränderliche Designentscheidungen

* Cloudflare Turnstile, kein alternatives CAPTCHA.
* ES256 JWT, kein RS, kein HS.
* Postgres Prod, SQLite nur lokal.
* Alembic, kein Flyway/Liquibase.
* FastAPI Monolith mit modularen Services, keine Microservices in v1.
