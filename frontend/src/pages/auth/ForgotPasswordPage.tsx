import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { authApi } from '../../lib/authApi'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      await authApi.forgotPassword(email.trim().toLowerCase())
      setSubmitted(true)
    } catch (err) {
      // Always show success message for security (don't reveal if email exists)
      setSubmitted(true)
    } finally {
      setIsLoading(false)
    }
  }

  if (submitted) {
    return (
      <AuthLayout title="Check your email">
        <div className="text-center space-y-4">
          <div className="rounded-lg border border-sky-500/40 bg-sky-500/10 px-4 py-6 text-sm text-sky-200">
            <p className="font-medium mb-2">
              📧 If that email is registered, we've sent password reset instructions.
            </p>
            <p className="text-xs text-sky-300/80">
              The reset link will be valid for 1 hour. Please check your inbox.
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
    <AuthLayout
      title="Reset your password"
      subtitle="Enter your email and we'll send you reset instructions"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
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

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? 'Sending...' : 'Send reset instructions'}
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
