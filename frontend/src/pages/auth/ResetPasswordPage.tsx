import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { authApi } from '../../lib/authApi'

export function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const token = searchParams.get('token')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!token) {
      setError('Invalid or missing reset token.')
      return
    }

    if (password.length < 10) {
      setError('Password must be at least 10 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsLoading(true)

    try {
      await authApi.resetPassword(token, password)
      setSuccess(true)

      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (err: any) {
      if (err.status === 400) {
        setError('Invalid or expired reset link. Please request a new one.')
      } else {
        setError(err.detail || 'Password reset failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <AuthLayout title="Invalid reset link">
        <div className="text-center space-y-4">
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-6 text-sm text-red-200">
            <p>The password reset link is invalid or missing.</p>
          </div>
          <Link
            to="/forgot-password"
            className="inline-block text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Request a new reset link
          </Link>
        </div>
      </AuthLayout>
    )
  }

  if (success) {
    return (
      <AuthLayout title="Password reset successful">
        <div className="text-center space-y-4">
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-6 text-sm text-emerald-200">
            <p className="font-medium mb-2">✓ Your password has been reset successfully!</p>
            <p className="text-xs text-emerald-300/80">
              Redirecting you to sign in...
            </p>
          </div>
          <Link
            to="/login"
            className="inline-block text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Go to sign in now →
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Set new password" subtitle="Choose a strong password">
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
            New password
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
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-2">
            Confirm new password
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

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? 'Resetting password...' : 'Reset password'}
        </Button>

        <p className="text-center text-sm text-slate-400">
          Remember your password?{' '}
          <Link to="/login" className="text-sky-400 hover:text-sky-300 transition-colors">
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
