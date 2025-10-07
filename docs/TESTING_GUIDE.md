# Testing Guide

Last Updated: 2025-10-07

## Quick Start Testing

This guide walks through testing the complete authentication flow locally.

## Prerequisites

1. **Backend running** on `http://localhost:8000`
2. **Frontend running** on `http://localhost:5173`
3. **PostgreSQL** running with migrations applied
4. **Redis** running
5. **Mailhog/SMTP** running on `localhost:1025` for email testing

## Local Development Setup

### 1. Start Backend

```bash
cd /path/to/backend
source venv/bin/activate

# Apply migrations
alembic upgrade head

# Start Celery worker (for emails)
celery -A app.celery_app worker --loglevel=info &

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Frontend

```bash
cd /path/to/frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 3. Start Mailhog (Email Testing)

```bash
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

View emails at `http://localhost:8025`

---

## Test Scenarios

### Scenario 1: New User Registration

**Steps:**
1. Navigate to `http://localhost:5173`
2. You should be redirected to `/login`
3. Click "Create an account" → redirected to `/register`
4. Fill in:
   - Email: `test@example.com`
   - Password: `StrongPassword123!`
   - Confirm Password: `StrongPassword123!`
5. Complete Turnstile CAPTCHA (test key auto-passes)
6. Click "Create Account"
7. Should see success message: "Registration almost done — check your email..."

**Expected Backend Response:**
```json
{
  "message": "Registration almost done — check your email. The link is valid for 24 hours."
}
```

**Verify:**
- Check Mailhog (`http://localhost:8025`) for verification email
- Email should contain a verification link with token

---

### Scenario 2: Email Verification

**Steps:**
1. From Mailhog, copy the verification link (looks like `/verify-email?token=xxx`)
2. Click the link or navigate to it
3. Should see success message and auto-redirect to login

**Expected Backend Response:**
```json
{
  "message": "Your email has been verified. You can now log in."
}
```

**Verify:**
- User record in database has `email_verified = true`
- Token is marked as used

---

### Scenario 3: Login (Without 2FA)

**Steps:**
1. Navigate to `/login`
2. Enter:
   - Email: `test@example.com`
   - Password: `StrongPassword123!`
3. Click "Sign In"
4. Should be redirected to `/` (dashboard)

**Expected Backend Response:**
```json
{
  "requires2fa": false,
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "expiresIn": 420
}
```

**Verify:**
- Tokens stored in localStorage/sessionStorage
- User info fetched and displayed
- Protected routes are accessible

---

### Scenario 4: Enable 2FA

**Steps:**
1. While logged in, navigate to `/account/security`
2. In "Two-Factor Authentication" section, click "Enable 2FA"
3. Should redirect to `/2fa/setup`
4. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
   - OR copy the manual entry code
5. Enter the 6-digit OTP from your app
6. Click "Enable 2FA"
7. Should see recovery codes displayed
8. **Important:** Save these recovery codes!
9. Click "I've Saved My Recovery Codes"

**Expected Backend Response (Init):**
```json
{
  "secret": "BASE32SECRET",
  "otpauthUrl": "otpauth://totp/...",
  "qrSvg": "<svg>...</svg>",
  "challengeId": "uuid"
}
```

**Expected Backend Response (Complete):**
```json
{
  "recoveryCodes": [
    "AAAA-BBBB-CCCC-1111",
    "DDDD-EEEE-FFFF-2222",
    ...
  ]
}
```

**Verify:**
- User record has `mfa_enabled = true`
- Recovery codes stored in database (hashed)
- Session is still active

---

### Scenario 5: Login with 2FA

**Steps:**
1. Log out (click profile → Log Out)
2. Navigate to `/login`
3. Enter email and password
4. Click "Sign In"
5. Should be redirected to `/2fa/verify`
6. Open authenticator app, get current 6-digit code
7. Enter the code
8. Click "Verify"
9. Should be logged in and redirected to `/`

**Expected Backend Response (Login):**
```json
{
  "requires2fa": true,
  "challengeId": "uuid"
}
```

**Expected Backend Response (Verify):**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "expiresIn": 420
}
```

**Verify:**
- Tokens stored correctly
- User is fully authenticated
- Dashboard loads

---

### Scenario 6: Forgot Password Flow

**Steps:**
1. Log out
2. On login page, click "Forgot password?"
3. Enter email: `test@example.com`
4. Click "Send Reset Link"
5. Check Mailhog for password reset email
6. Click the reset link (or copy URL)
7. Should navigate to `/reset-password?token=xxx`
8. Enter new password: `NewStrongPassword456!`
9. Confirm password
10. Click "Reset Password"
11. Should see success and redirect to login
12. Log in with new password

**Expected Backend Response:**
```json
{
  "message": "Password has been reset successfully."
}
```

**Verify:**
- Can log in with new password
- Old password no longer works
- Token is one-time use only

---

### Scenario 7: Recovery Code Login

**Steps:**
1. Ensure 2FA is enabled (Scenario 4)
2. Log out
3. Log in with email and password
4. On 2FA verify page, click "Use recovery code instead"
5. Enter one of your saved recovery codes
6. Click "Verify"
7. Should be logged in

**Expected Backend Response:**
```json
{
  "accessToken": "eyJ...",
  "refreshToken": "eyJ...",
  "expiresIn": 420
}
```

**Verify:**
- Successfully logged in
- Recovery code is marked as used (can't be reused)
- 9 codes remaining

---

### Scenario 8: Adaptive CAPTCHA (After Failed Logins)

**Steps:**
1. Log out
2. Attempt to log in with **wrong password** 3 times
3. On 4th attempt, backend should return 400 with "Captcha required."
4. Frontend should show Turnstile widget
5. Complete CAPTCHA
6. Enter correct credentials
7. Should log in successfully

**Expected Backend Error:**
```json
{
  "detail": "Captcha required."
}
```

**Verify:**
- CAPTCHA appears after failures
- Login succeeds after completing CAPTCHA

---

### Scenario 9: Account Lockout (5 Failed Attempts)

**Steps:**
1. Log out
2. Attempt to log in with wrong password 5 times
3. Account should be locked for 5 minutes
4. Attempt to log in with **correct** password
5. Should see error: "Too many failed login attempts. Try again in X minutes."

**Expected Backend Error:**
```json
{
  "detail": "Too many failed login attempts. Try again in 5 minutes."
}
```

**Verify:**
- Account is locked even with correct password
- Error shows time remaining
- Can log in after 5 minutes

---

### Scenario 10: Disable 2FA

**Steps:**
1. Log in (with 2FA if enabled)
2. Navigate to `/account/security`
3. In "Two-Factor Authentication" section, click "Disable 2FA"
4. Enter your password
5. Enter current 6-digit OTP from authenticator app
6. Click "Disable 2FA"
7. Should see success message
8. Log out and log in again - no 2FA required

**Expected Backend Response:**
```json
{
  "message": "Two-factor authentication has been disabled."
}
```

**Verify:**
- User record has `mfa_enabled = false`
- Recovery codes cleared
- Login no longer requires OTP

---

## API Testing with cURL

### Register
```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "StrongPassword123!",
    "captchaToken": "DUMMY_TOKEN"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "StrongPassword123!"
  }'
```

### Get User Info
```bash
curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Enable 2FA Init
```bash
curl -X POST http://localhost:8000/v1/auth/2fa/enable-init \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Database Verification

### Check User Status
```sql
SELECT id, email, email_verified, mfa_enabled, status, failed_login_attempts
FROM users
WHERE email = 'test@example.com';
```

### Check Active Sessions
```sql
SELECT s.id, s.user_id, s.expires_at, s.ip_address, s.user_agent
FROM sessions s
JOIN users u ON s.user_id = u.id
WHERE u.email = 'test@example.com' AND s.expires_at > NOW();
```

### Check Audit Logs
```sql
SELECT action, resource_type, resource_id, details, created_at
FROM audit_logs
WHERE user_id = (SELECT id FROM users WHERE email = 'test@example.com')
ORDER BY created_at DESC
LIMIT 10;
```

---

## Common Issues

### Frontend shows white page
- **Cause:** Build errors or auth pages not implemented
- **Fix:** Run `npm run build` and check for TypeScript errors

### CAPTCHA doesn't show
- **Cause:** Missing Turnstile script or wrong site key
- **Fix:** Check `VITE_TURNSTILE_SITE_KEY` in `.env`

### Emails not received
- **Cause:** Celery worker not running or SMTP not configured
- **Fix:** Check Celery logs and verify Mailhog is running

### 401 Unauthorized on protected routes
- **Cause:** Token expired or not stored
- **Fix:** Check browser localStorage/sessionStorage for tokens

### Token refresh not working
- **Cause:** Refresh token expired or invalidated
- **Fix:** Log out and log in again

---

## Performance Testing

### Login Endpoint (Target: 200 RPS, p95 < 150ms)

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test login endpoint
ab -n 1000 -c 10 -p login.json -T application/json \
  http://localhost:8000/v1/auth/login
```

**login.json:**
```json
{
  "email": "test@example.com",
  "password": "StrongPassword123!"
}
```

### Expected Results:
- Requests per second: > 200
- Time per request (mean): < 50ms
- Time per request (95th percentile): < 150ms

---

## Security Testing

### Test Rate Limiting
```bash
# Should get 429 Too Many Requests after limit
for i in {1..100}; do
  curl -X POST http://localhost:8000/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' \
    -w "\n%{http_code}\n"
done
```

### Test Token Expiry
```bash
# Wait 8 minutes after login, then try to use access token
# Should get 401 Unauthorized

curl -X GET http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer EXPIRED_TOKEN"
```

### Test CORS
```bash
# Should reject requests from unauthorized origins
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Origin: http://evil.com" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}'
```

---

## Next Steps

1. **Run all test scenarios** above to verify functionality
2. **Check audit logs** to ensure all security events are tracked
3. **Test edge cases** (expired tokens, invalid OTPs, etc.)
4. **Load test** critical endpoints
5. **Review security headers** in browser DevTools
6. **Configure production secrets** (see `docs/CONFIGURATION.md`)
7. **Deploy to staging** (see `docs/DEPLOYMENT.md`)

---

## References

- **API Docs:** http://localhost:8000/docs
- **Configuration:** `docs/CONFIGURATION.md`
- **Deployment:** `docs/DEPLOYMENT.md`
- **Implementation Status:** `docs/IMPLEMENTATION_STATUS.md`
