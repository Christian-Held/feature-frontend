import { useNavigate } from 'react-router-dom'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { useAuthStore } from '../../stores/authStore'

export function SecurityPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const handleEnable2FA = () => {
    navigate('/2fa/setup')
  }

  const handleDisable2FA = () => {
    // TODO: Implement disable 2FA modal with password + OTP verification
    alert('Disable 2FA - Coming soon')
  }

  const handleChangePassword = () => {
    // TODO: Implement change password modal
    alert('Change password - Coming soon')
  }

  const handleViewSessions = () => {
    // TODO: Implement sessions viewer
    alert('View sessions - Coming soon')
  }

  return (
    <AppShell>
      <Header
        title="Security"
        description="Manage your account security settings"
      />
      <div className="flex-1 p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Two-Factor Authentication */}
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">Two-Factor Authentication</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Add an extra layer of security to your account
                </p>
              </div>
              <Badge variant={user?.mfaEnabled ? 'success' : 'secondary'}>
                {user?.mfaEnabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>

            {user?.mfaEnabled ? (
              <div className="space-y-4">
                <div className="bg-emerald-500/10 border border-emerald-500/40 rounded-lg p-4">
                  <p className="text-sm text-emerald-200">
                    ✓ Two-factor authentication is enabled on your account. You'll be asked for a
                    code when signing in.
                  </p>
                </div>
                <Button type="button" variant="outline" onClick={handleDisable2FA}>
                  Disable 2FA
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-amber-500/10 border border-amber-500/40 rounded-lg p-4">
                  <p className="text-sm text-amber-200">
                    ⚠️ Your account is not protected by two-factor authentication. Enable it now for
                    better security.
                  </p>
                </div>
                <Button type="button" onClick={handleEnable2FA}>
                  Enable 2FA
                </Button>
              </div>
            )}
          </div>

          {/* Password */}
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">Password</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Change your password regularly to keep your account secure
                </p>
              </div>
            </div>
            <Button type="button" variant="outline" onClick={handleChangePassword}>
              Change password
            </Button>
          </div>

          {/* Active Sessions */}
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-100">Active Sessions</h3>
                <p className="text-sm text-slate-400 mt-1">
                  Manage devices and browsers where you're currently signed in
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <Button type="button" variant="outline" onClick={handleViewSessions}>
                View all sessions
              </Button>
              <div className="text-xs text-slate-500">
                You can sign out from other devices if you notice any suspicious activity
              </div>
            </div>
          </div>

          {/* Account Status */}
          <div className="rounded-2xl border border-slate-800/70 bg-slate-950/60 p-6">
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Account Status</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Email verified</span>
                <Badge variant={user?.emailVerified ? 'success' : 'secondary'}>
                  {user?.emailVerified ? 'Verified' : 'Unverified'}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Account status</span>
                <Badge variant={user?.status === 'ACTIVE' ? 'success' : 'secondary'}>
                  {user?.status}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Two-factor authentication</span>
                <Badge variant={user?.mfaEnabled ? 'success' : 'secondary'}>
                  {user?.mfaEnabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
