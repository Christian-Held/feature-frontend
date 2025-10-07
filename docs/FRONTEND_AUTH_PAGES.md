# Missing Frontend Auth Pages

The backend auth API is complete, but the following frontend pages need to be implemented per the specification.

## 📋 Required Pages

### Public Routes (Unauthenticated)

1. `/login` - Login page
2. `/register` - Registration page
3. `/verify-email` - Email verification confirmation
4. `/forgot-password` - Request password reset
5. `/reset-password` - Reset password with token
6. `/2fa/setup` - Two-factor authentication setup (after login)
7. `/2fa/verify` - Two-factor authentication verification

### Authenticated Routes (Existing)

✅ `/` - Dashboard (exists)
✅ `/account/billing` - Plan management (exists)
✅ `/account/limits` - Spend limits (exists)
✅ `/account/security` - Security settings (needs creation)
✅ `/admin/users` - Admin user management (exists)
✅ `/admin/audit-logs` - Audit logs viewer (exists)

---

## 🚀 Implementation Guide

### Prerequisites

Create the following utilities first:

#### 1. API Client for Auth (`frontend/src/lib/authApi.ts`)

```typescript
import { apiClient } from './api'

export interface RegisterRequest {
  email: string
  password: string
  captchaToken: string
}

export interface LoginRequest {
  email: string
  password: string
  captchaToken?: string
}

export interface LoginResponse {
  requires2fa: boolean
  challengeId?: string
  accessToken?: string
  refreshToken?: string
  expiresIn?: number
}

export const authApi = {
  register: (data: RegisterRequest) =>
    apiClient.post('/v1/auth/register', data),

  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/v1/auth/login', data),

  verify2FA: (challengeId: string, otp: string, captchaToken?: string) =>
    apiClient.post('/v1/auth/2fa/verify', { challengeId, otp, captchaToken }),

  verifyEmail: (token: string) =>
    apiClient.get(`/v1/auth/verify-email?token=${token}`),

  forgotPassword: (email: string) =>
    apiClient.post('/v1/auth/forgot-password', { email }),

  resetPassword: (token: string, newPassword: string) =>
    apiClient.post('/v1/auth/reset-password', { token, newPassword }),

  resendVerification: (email: string) =>
    apiClient.post('/v1/auth/resend-verification', { email }),

  // 2FA Management
  enable2FAInit: () =>
    apiClient.post('/v1/auth/2fa/enable-init'),

  enable2FAComplete: (challengeId: string, otp: string) =>
    apiClient.post('/v1/auth/2fa/enable-complete', { challengeId, otp }),

  disable2FA: (password: string, otp: string) =>
    apiClient.post('/v1/auth/2fa/disable', { password, otp }),

  // Session
  logout: (refreshToken: string) =>
    apiClient.post('/v1/auth/logout', { refreshToken }),

  refresh: (refreshToken: string) =>
    apiClient.post('/v1/auth/refresh', { refreshToken }),

  me: () =>
    apiClient.get('/v1/auth/me'),
}
```

#### 2. Auth Store (`frontend/src/stores/authStore.ts`)

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: { id: string; email: string } | null
  setTokens: (access: string, refresh: string) => void
  clearAuth: () => void
  setUser: (user: { id: string; email: string }) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),
      clearAuth: () =>
        set({ accessToken: null, refreshToken: null, user: null }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    },
  ),
)
```

#### 3. Turnstile Component (`frontend/src/components/auth/TurnstileWidget.tsx`)

```typescript
import { useEffect, useRef } from 'react'

interface TurnstileWidgetProps {
  siteKey: string
  onVerify: (token: string) => void
  onError?: () => void
}

export function TurnstileWidget({
  siteKey,
  onVerify,
  onError,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
    script.async = true
    script.defer = true
    document.body.appendChild(script)

    script.onload = () => {
      window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: onVerify,
        'error-callback': onError,
      })
    }

    return () => {
      document.body.removeChild(script)
    }
  }, [siteKey, onVerify, onError])

  return <div ref={containerRef} />
}
```

---

## 📄 Page Templates

### 1. Login Page (`frontend/src/pages/auth/LoginPage.tsx`)

**Route:** `/login`

**Features:**
- Email + password fields
- Show CAPTCHA after 3 failed attempts (handle via backend 400 response)
- Remember me checkbox (optional)
- Link to `/forgot-password`
- Link to `/register`

**Key Behaviors:**
- On success without 2FA: Store tokens, redirect to `/`
- On success with 2FA: Redirect to `/2fa/verify` with `challengeId`
- Show exact error messages from spec:
  - "Email or password is incorrect."
  - "You must confirm your registration first. We've sent you an email."
  - "Captcha required."

**Example Structure:**

```typescript
export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [showCaptcha, setShowCaptcha] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { setTokens } = useAuthStore()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      const response = await authApi.login({ email, password, captchaToken })
      if (response.requires2fa) {
        navigate('/2fa/verify', { state: { challengeId: response.challengeId } })
      } else {
        setTokens(response.accessToken!, response.refreshToken!)
        navigate('/')
      }
    } catch (err) {
      if (err.status === 400 && err.detail === 'Captcha required.') {
        setShowCaptcha(true)
      }
      setError(err.detail || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4 p-8">
        <h1>Sign in to your account</h1>
        {error && <div className="text-red-400">{error}</div>}
        <Input type="email" value={email} onChange={e => setEmail(e.target.value)} />
        <Input type="password" value={password} onChange={e => setPassword(e.target.value)} />
        {showCaptcha && <TurnstileWidget siteKey="..." onVerify={setCaptchaToken} />}
        <Button type="submit">Sign in</Button>
        <a href="/forgot-password">Forgot password?</a>
        <a href="/register">Create account</a>
      </form>
    </div>
  )
}
```

---

### 2. Registration Page (`frontend/src/pages/auth/RegisterPage.tsx`)

**Route:** `/register`

**Features:**
- Email field
- Password field (min 10 chars, show strength meter)
- Cloudflare Turnstile CAPTCHA (always shown)
- Link to `/login`

**Key Behaviors:**
- On success: Show message "Registration almost done — check your email. The link is valid for 24 hours."
- Password validation: Min 10 characters
- Show exact error messages from backend

**Example:**

```typescript
export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await authApi.register({ email, password, captchaToken })
    setSuccess(true)
  }

  if (success) {
    return (
      <div className="text-center">
        <p>Registration almost done — check your email. The link is valid for 24 hours.</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit}>
      <Input type="email" value={email} onChange={e => setEmail(e.target.value)} />
      <Input type="password" minLength={10} value={password} onChange={e => setPassword(e.target.value)} />
      <TurnstileWidget siteKey="..." onVerify={setCaptchaToken} />
      <Button type="submit">Create account</Button>
    </form>
  )
}
```

---

### 3. Email Verification Page (`frontend/src/pages/auth/VerifyEmailPage.tsx`)

**Route:** `/verify-email?token=...`

**Features:**
- Extract token from URL query param
- Auto-verify on mount
- Show success/error message
- Redirect to `/login` after 3 seconds on success

**Example:**

```typescript
export function VerifyEmailPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setStatus('error')
      return
    }

    authApi.verifyEmail(token)
      .then(() => {
        setStatus('success')
        setTimeout(() => navigate('/login?verified=1'), 3000)
      })
      .catch(() => setStatus('error'))
  }, [])

  if (status === 'loading') return <Spinner />
  if (status === 'success') return <div>Email verified! Redirecting to login...</div>
  return <div>Verification failed or expired. Please request a new link.</div>
}
```

---

### 4. Forgot Password Page (`frontend/src/pages/auth/ForgotPasswordPage.tsx`)

**Route:** `/forgot-password`

**Features:**
- Email field
- Submit button

**Key Behaviors:**
- Always show success message (even if email doesn't exist, for security)
- Message: "If that email is registered, we've sent password reset instructions."

---

### 5. Reset Password Page (`frontend/src/pages/auth/ResetPasswordPage.tsx`)

**Route:** `/reset-password?token=...`

**Features:**
- Extract token from URL query
- New password field (min 10 chars)
- Confirm password field

**Key Behaviors:**
- On success: Redirect to `/login` with message
- On error: Show "Invalid or expired reset link"

---

### 6. 2FA Setup Page (`frontend/src/pages/auth/TwoFactorSetupPage.tsx`)

**Route:** `/2fa/setup` (authenticated)

**Features:**
- Call `/v1/auth/2fa/enable-init` to get QR code
- Display QR code (from `qr_svg`) and manual entry code
- Input field for OTP verification
- Show recovery codes after successful setup (one-time display + download)

---

### 7. 2FA Verify Page (`frontend/src/pages/auth/TwoFactorVerifyPage.tsx`)

**Route:** `/2fa/verify` (receives `challengeId` from login)

**Features:**
- 6-digit OTP input
- Submit button
- Show CAPTCHA after 5 failed attempts

**Key Behaviors:**
- On success: Store tokens, redirect to `/`
- Show error: "Invalid security code."

---

### 8. Account Security Page (`frontend/src/pages/account/SecurityPage.tsx`)

**Route:** `/account/security` (authenticated)

**Features:**
- Change password form
- Enable/Disable 2FA toggle
- Active sessions list with "Sign out others" button

**API Calls:**
- `POST /v1/auth/2fa/enable-init`
- `POST /v1/auth/2fa/enable-complete`
- `POST /v1/auth/2fa/disable`
- Get sessions from backend (needs implementation)

---

## 🎨 UI/UX Notes

### Exact Error Messages (Per Spec Section 17)

Use these EXACT messages in your frontend:

```typescript
const ERROR_MESSAGES = {
  REGISTRATION_SUCCESS: "Registration almost done — check your email. The link is valid for 24 hours.",
  UNVERIFIED: "You must confirm your registration first. We've sent you an email.",
  INVALID_OTP: "Invalid security code.",
  CAPTCHA_REQUIRED: "Captcha required.",
  UNAUTHORIZED: "You don't have permission to perform this action.",
  CAP_REACHED: "Your monthly spending limit has been reached. Adjust your limit to continue.",
  WRONG_CREDENTIALS: "Email or password is incorrect.",
}
```

### Consistent Styling

All auth pages should use the same dark theme as existing pages:
- Background: `bg-slate-950`
- Cards: `bg-slate-950/60` with `border-slate-800/70`
- Text: `text-slate-100` (headings), `text-slate-300` (body)
- Inputs: Use existing `Input` component
- Buttons: Use existing `Button` component with `variant="primary"`

### Loading States

Use existing `Spinner` component for all async operations.

---

## 🔧 App Router Updates

Update `frontend/src/App.tsx`:

```typescript
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { VerifyEmailPage } from './pages/auth/VerifyEmailPage'
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage'
import { TwoFactorVerifyPage } from './pages/auth/TwoFactorVerifyPage'
import { TwoFactorSetupPage } from './pages/auth/TwoFactorSetupPage'
import { SecurityPage } from './pages/account/SecurityPage'

export function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/2fa/verify" element={<TwoFactorVerifyPage />} />

      {/* Authenticated routes */}
      <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/account/security" element={<ProtectedRoute><SecurityPage /></ProtectedRoute>} />
      <Route path="/2fa/setup" element={<ProtectedRoute><TwoFactorSetupPage /></ProtectedRoute>} />

      {/* ... existing routes */}
    </Routes>
  )
}
```

---

## ✅ Checklist

Before considering auth implementation complete:

- [ ] All 7 public auth pages created
- [ ] `/account/security` page created
- [ ] Auth API client functions implemented
- [ ] Auth store (Zustand) implemented
- [ ] Turnstile widget component created
- [ ] Protected route wrapper implemented
- [ ] 401 interceptor for auto-refresh implemented
- [ ] Error messages match spec exactly
- [ ] Password strength meter on register/reset
- [ ] Recovery codes download on 2FA setup
- [ ] "Sign out others" functionality
- [ ] Responsive mobile design
- [ ] Loading states for all async actions
- [ ] Form validation (client + server)

---

## 📚 Additional Resources

- **Cloudflare Turnstile Docs:** https://developers.cloudflare.com/turnstile/
- **React Router Docs:** https://reactrouter.com/
- **Zustand Docs:** https://docs.pmnd.rs/zustand/
- **Backend API Schema:** See `backend/auth/schemas.py`
- **Spec Reference:** See main specification document section 4 (API) and section 5 (User Flows)

---

## 🐛 Testing

Create test users:

```bash
# Using admin panel at /admin/users after logging in as admin
# Or via API:
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123",
    "captchaToken": "DUMMY_TOKEN"
  }'
```

---

**Status:** Backend complete ✅ | Frontend pages need implementation ⚠️

Estimated effort: 2-3 days for experienced React developer
