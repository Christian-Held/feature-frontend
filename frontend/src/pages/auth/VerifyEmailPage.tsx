import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AuthLayout } from '../../components/auth/AuthLayout'
import { Spinner } from '../../components/ui/Spinner'
import { authApi } from '../../lib/authApi'

export function VerifyEmailPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const token = searchParams.get('token')

    if (!token) {
      setStatus('error')
      setErrorMessage('No verification token provided.')
      return
    }

    authApi
      .verifyEmail(token)
      .then(() => {
        setStatus('success')
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login?verified=1')
        }, 3000)
      })
      .catch((err) => {
        setStatus('error')
        setErrorMessage(err.detail || 'Verification failed or link expired.')
      })
  }, [searchParams, navigate])

  if (status === 'loading') {
    return (
      <AuthLayout title="Verifying your email">
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <Spinner />
          <p className="text-sm text-slate-400">Please wait while we verify your email...</p>
        </div>
      </AuthLayout>
    )
  }

  if (status === 'success') {
    return (
      <AuthLayout title="Email verified!">
        <div className="text-center space-y-4">
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-6">
            <p className="text-emerald-200 font-medium mb-2">✓ Your email has been verified successfully!</p>
            <p className="text-sm text-emerald-300/80">
              Redirecting you to sign in...
            </p>
          </div>
          <Link
            to="/login?verified=1"
            className="inline-block text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Go to sign in now →
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Verification failed">
      <div className="text-center space-y-4">
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-6">
          <p className="text-red-200 font-medium mb-2">✗ {errorMessage}</p>
          <p className="text-sm text-red-300/80">
            The verification link may have expired or is invalid.
          </p>
        </div>
        <div className="flex flex-col items-center gap-3">
          <Link
            to="/login"
            className="text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Back to sign in
          </Link>
          <span className="text-slate-500 text-sm">or</span>
          <Link
            to="/register"
            className="text-sky-400 hover:text-sky-300 transition-colors text-sm"
          >
            Create a new account
          </Link>
        </div>
      </div>
    </AuthLayout>
  )
}
