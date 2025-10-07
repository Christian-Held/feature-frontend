import type { FormEvent } from 'react'
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { TurnstileWidget } from '../../components/auth/TurnstileWidget'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { authApi } from '../../lib/authApi'
import { ERROR_MESSAGES, TURNSTILE_SITE_KEY } from '../../lib/constants'
import { useAuthStore } from '../../stores/authStore'

export function TwoFactorVerifyPage() {
  const [otp, setOtp] = useState('')
  const [captchaToken, setCaptchaToken] = useState('')
  const [showCaptcha, setShowCaptcha] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const location = useLocation()
  const navigate = useNavigate()
  const { setTokens, setUser } = useAuthStore()

  const { challengeId, email } = location.state || {}

  if (!challengeId) {
    navigate('/login')
    return null
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const response = await authApi.verify2FA({
        challengeId,
        otp: otp.trim(),
        captchaToken: showCaptcha ? captchaToken : undefined,
      })

      // Store tokens
      setTokens(response.accessToken, response.refreshToken)

      // Fetch user info
      const userInfo = await authApi.me(response.accessToken)
      setUser(userInfo)

      // Redirect to dashboard
      navigate('/')
    } catch (err: any) {
      if (err.status === 400) {
        if (err.detail === 'Captcha required.') {
          setShowCaptcha(true)
          setError(ERROR_MESSAGES.CAPTCHA_REQUIRED)
        } else if (err.detail === ERROR_MESSAGES.INVALID_OTP) {
          setError(ERROR_MESSAGES.INVALID_OTP)
        } else {
          setError(err.detail || 'Verification failed.')
        }
      } else if (err.status === 423) {
        setError('Account temporarily locked. Please try again later.')
      } else {
        setError(err.detail || 'Verification failed.')
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
      title="Two-factor authentication"
      subtitle={email ? `Verifying ${email}` : 'Enter your security code'}
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="otp" className="block text-sm font-medium text-slate-300 mb-2">
            Authentication code
          </label>
          <Input
            id="otp"
            type="text"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
            required
            pattern="[0-9]{6}"
            maxLength={6}
            placeholder="000000"
            disabled={isLoading}
            className="text-center text-2xl tracking-widest font-mono"
          />
          <p className="mt-2 text-xs text-slate-500">
            Enter the 6-digit code from your authenticator app
          </p>
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

        <Button
          type="submit"
          className="w-full"
          disabled={isLoading || otp.length !== 6 || (showCaptcha && !captchaToken)}
        >
          {isLoading ? 'Verifying...' : 'Verify'}
        </Button>

        <div className="text-center">
          <button
            type="button"
            onClick={() => navigate('/login')}
            className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            ← Back to sign in
          </button>
        </div>
      </form>
    </AuthLayout>
  )
}
