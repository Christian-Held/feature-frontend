import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { TurnstileWidget } from '../../components/auth/TurnstileWidget'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { authApi } from '../../lib/authApi'
import { TURNSTILE_SITE_KEY } from '../../lib/constants'
import { useAuthStore } from '../../stores/authStore'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [showCaptcha, setShowCaptcha] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setTokens, setUser } = useAuthStore()

  const verified = searchParams.get('verified')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const response = await authApi.login({
        email: email.trim().toLowerCase(),
        password,
        captchaToken: showCaptcha ? captchaToken : undefined,
      })

      if (response.requires2fa) {
        // Redirect to 2FA verification
        navigate('/2fa/verify', {
          state: { challengeId: response.challengeId, email },
        })
      } else {
        // Store tokens and fetch user info
        setTokens(response.accessToken!, response.refreshToken!)

        // Fetch user info
        const userInfo = await authApi.me(response.accessToken!)
        setUser(userInfo)

        // Redirect to dashboard
        navigate('/')
      }
    } catch (err: any) {
      if (err.status === 400 && err.detail === 'Captcha required.') {
        setShowCaptcha(true)
        setError(err.detail)
      } else if (err.status === 403) {
        setError(err.detail || "You must confirm your registration first. We've sent you an email.")
      } else if (err.status === 401) {
        setError('Email or password is incorrect.')
      } else {
        setError(err.detail || 'Login failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleCaptchaVerify = (token: string) => {
    setCaptchaToken(token)
    setError('')
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle={verified === '1' ? 'Email verified! You can now sign in.' : undefined}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
            Email address
          </label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="you@example.com"
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
            Password
          </label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            placeholder="Enter your password"
            disabled={isLoading}
          />
        </div>

        {showCaptcha && (
          <div>
            <TurnstileWidget
              siteKey={TURNSTILE_SITE_KEY}
              onVerify={handleCaptchaVerify}
              onError={() => setError('CAPTCHA verification failed. Please try again.')}
            />
          </div>
        )}

        <Button type="submit" className="w-full" disabled={isLoading || (showCaptcha && !captchaToken)}>
          {isLoading ? 'Signing in...' : 'Sign in'}
        </Button>

        <div className="flex items-center justify-between text-sm">
          <Link
            to="/forgot-password"
            className="text-sky-400 hover:text-sky-300 transition-colors"
          >
            Forgot password?
          </Link>
          <Link
            to="/register"
            className="text-sky-400 hover:text-sky-300 transition-colors"
          >
            Create account
          </Link>
        </div>
      </form>
    </AuthLayout>
  )
}
