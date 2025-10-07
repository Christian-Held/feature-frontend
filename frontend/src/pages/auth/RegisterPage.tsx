import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { TurnstileWidget } from '../../components/auth/TurnstileWidget'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { authApi } from '../../lib/authApi'
import { ERROR_MESSAGES, TURNSTILE_SITE_KEY } from '../../lib/constants'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const passwordStrength = getPasswordStrength(password)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    // Validation
    if (password.length < 10) {
      setError('Password must be at least 10 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    if (!captchaToken) {
      setError('Please complete the CAPTCHA verification.')
      return
    }

    setIsLoading(true)

    try {
      await authApi.register({
        email: email.trim().toLowerCase(),
        password,
        captchaToken,
      })

      setSuccess(true)
    } catch (err: any) {
      if (err.status === 409) {
        setError('An account with this email already exists.')
      } else {
        setError(err.detail || 'Registration failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleCaptchaVerify = (token: string) => {
    setCaptchaToken(token)
    setError('')
  }

  if (success) {
    return (
      <AuthLayout title="Check your email">
        <div className="text-center space-y-4">
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-6 text-sm text-emerald-200">
            <p className="font-medium mb-2">📧 {ERROR_MESSAGES.REGISTRATION_SUCCESS}</p>
            <p className="text-xs text-emerald-300/80">
              Please check your inbox and click the verification link to activate your account.
            </p>
          </div>
          <Link
            to="/login"
            className="inline-block text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Back to sign in
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Create your account" subtitle="Start your journey with us">
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
            minLength={10}
            autoComplete="new-password"
            placeholder="Minimum 10 characters"
            disabled={isLoading}
          />
          {password && (
            <div className="mt-2">
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      passwordStrength === 'weak'
                        ? 'w-1/3 bg-red-500'
                        : passwordStrength === 'medium'
                        ? 'w-2/3 bg-yellow-500'
                        : 'w-full bg-emerald-500'
                    }`}
                  />
                </div>
                <span className="text-xs text-slate-400 capitalize">{passwordStrength}</span>
              </div>
              <p className="text-xs text-slate-500">
                Use a mix of letters, numbers, and symbols for better security
              </p>
            </div>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-2">
            Confirm password
          </label>
          <Input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
            placeholder="Re-enter your password"
            disabled={isLoading}
          />
        </div>

        <div>
          <TurnstileWidget
            siteKey={TURNSTILE_SITE_KEY}
            onVerify={handleCaptchaVerify}
            onError={() => setError('CAPTCHA verification failed. Please try again.')}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading || !captchaToken}>
          {isLoading ? 'Creating account...' : 'Create account'}
        </Button>

        <p className="text-center text-sm text-slate-400">
          Already have an account?{' '}
          <Link to="/login" className="text-sky-400 hover:text-sky-300 transition-colors">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}

function getPasswordStrength(password: string): 'weak' | 'medium' | 'strong' {
  if (password.length < 10) return 'weak'

  let score = 0
  if (password.length >= 12) score++
  if (/[a-z]/.test(password)) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password)) score++
  if (/[^a-zA-Z0-9]/.test(password)) score++

  if (score <= 2) return 'weak'
  if (score <= 4) return 'medium'
  return 'strong'
}
