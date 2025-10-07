import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Spinner } from '../../components/ui/Spinner'
import { authApi } from '../../lib/authApi'
import { ERROR_MESSAGES } from '../../lib/constants'
import { useAuthStore } from '../../stores/authStore'

export function TwoFactorSetupPage() {
  const [step, setStep] = useState<'init' | 'verify' | 'complete'>('init')
  const [secret, setSecret] = useState('')
  const [qrSvg, setQrSvg] = useState('')
  const [challengeId, setChallengeId] = useState('')
  const [otp, setOtp] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([])
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const navigate = useNavigate()
  const { accessToken, setUser } = useAuthStore()

  useEffect(() => {
    if (!accessToken) {
      navigate('/login')
      return
    }

    // Initialize 2FA setup
    setIsLoading(true)
    authApi
      .enable2FAInit(accessToken)
      .then((response) => {
        setSecret(response.secret)
        setQrSvg(response.qrSvg)
        setChallengeId(response.challengeId)
        setStep('verify')
      })
      .catch((err) => {
        setError(err.detail || 'Failed to initialize 2FA setup')
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [accessToken, navigate])

  const handleVerifySubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!accessToken) return

    setError('')
    setIsLoading(true)

    try {
      const response = await authApi.enable2FAComplete(accessToken, challengeId, otp.trim())
      setRecoveryCodes(response.recoveryCodes)
      setStep('complete')

      // Update user state to reflect MFA enabled
      const userInfo = await authApi.me(accessToken)
      setUser(userInfo)
    } catch (err: any) {
      if (err.detail === ERROR_MESSAGES.INVALID_OTP) {
        setError(ERROR_MESSAGES.INVALID_OTP)
      } else {
        setError(err.detail || 'Failed to enable 2FA')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const downloadRecoveryCodes = () => {
    const blob = new Blob(
      [
        `Two-Factor Authentication Recovery Codes\n`,
        `Generated: ${new Date().toISOString()}\n\n`,
        `Keep these codes safe! Each code can only be used once.\n\n`,
        recoveryCodes.join('\n'),
      ],
      { type: 'text/plain' }
    )
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'recovery-codes.txt'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const copyRecoveryCodes = () => {
    navigator.clipboard.writeText(recoveryCodes.join('\n'))
  }

  if (step === 'init' && isLoading) {
    return (
      <AppShell>
        <div className="flex min-h-screen items-center justify-center">
          <Spinner />
        </div>
      </AppShell>
    )
  }

  if (step === 'verify') {
    return (
      <AppShell>
        <Header
          title="Set up two-factor authentication"
          description="Scan the QR code with your authenticator app"
        />
        <div className="flex-1 p-6">
          <div className="max-w-2xl mx-auto">
            <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-8">
              {error && (
                <div className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-4">
                    Step 1: Scan QR Code
                  </h3>
                  <div className="flex justify-center bg-white p-4 rounded-lg">
                    <div dangerouslySetInnerHTML={{ __html: qrSvg }} />
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold text-slate-100 mb-2">
                    Or enter code manually
                  </h3>
                  <div className="bg-slate-900 p-3 rounded-lg font-mono text-sm text-slate-300 break-all">
                    {secret}
                  </div>
                </div>

                <form onSubmit={handleVerifySubmit} className="space-y-4">
                  <div>
                    <label htmlFor="otp" className="block text-sm font-medium text-slate-300 mb-2">
                      Step 2: Enter verification code
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
                  </div>

                  <div className="flex gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => navigate('/account/security')}
                      disabled={isLoading}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      className="flex-1"
                      disabled={isLoading || otp.length !== 6}
                    >
                      {isLoading ? 'Verifying...' : 'Enable 2FA'}
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </AppShell>
    )
  }

  if (step === 'complete') {
    return (
      <AppShell>
        <Header
          title="Two-factor authentication enabled"
          description="Save your recovery codes"
        />
        <div className="flex-1 p-6">
          <div className="max-w-2xl mx-auto">
            <div className="rounded-2xl border border-emerald-800/70 bg-emerald-950/30 p-8">
              <div className="space-y-6">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 mb-4">
                    <span className="text-3xl">✓</span>
                  </div>
                  <h3 className="text-xl font-semibold text-emerald-100 mb-2">
                    Two-factor authentication is now enabled
                  </h3>
                  <p className="text-sm text-emerald-200/80">
                    Your account is now more secure!
                  </p>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/40 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-amber-200 mb-2">
                    ⚠️ Save your recovery codes
                  </h4>
                  <p className="text-xs text-amber-300/80 mb-3">
                    Store these codes in a safe place. You'll need them if you lose access to your
                    authenticator app. Each code can only be used once.
                  </p>
                  <div className="bg-slate-900 p-3 rounded-lg font-mono text-sm text-slate-300 space-y-1">
                    {recoveryCodes.map((code, index) => (
                      <div key={index}>{code}</div>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button type="button" variant="outline" onClick={copyRecoveryCodes}>
                    Copy codes
                  </Button>
                  <Button type="button" variant="secondary" onClick={downloadRecoveryCodes}>
                    Download codes
                  </Button>
                  <Button
                    type="button"
                    className="flex-1"
                    onClick={() => navigate('/account/security')}
                  >
                    Done
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </AppShell>
    )
  }

  return null
}
