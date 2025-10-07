import { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { BillingPage } from './pages/account/BillingPage'
import { LimitsPage } from './pages/account/LimitsPage'
import { SecurityPage } from './pages/account/SecurityPage'
import { SettingsPage } from './pages/SettingsPage'
import { AdminUsersPage } from './pages/admin/AdminUsersPage'
import { AdminAuditLogsPage } from './pages/admin/AdminAuditLogsPage'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { VerifyEmailPage } from './pages/auth/VerifyEmailPage'
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage'
import { ResetPasswordPage } from './pages/auth/ResetPasswordPage'
import { TwoFactorVerifyPage } from './pages/auth/TwoFactorVerifyPage'
import { TwoFactorSetupPage } from './pages/auth/TwoFactorSetupPage'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { Spinner } from './components/ui/Spinner'

export function App() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
          <Spinner />
        </div>
      }
    >
      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/2fa/verify" element={<TwoFactorVerifyPage />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/account/billing"
          element={
            <ProtectedRoute>
              <BillingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/account/limits"
          element={
            <ProtectedRoute>
              <LimitsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/account/security"
          element={
            <ProtectedRoute>
              <SecurityPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/2fa/setup"
          element={
            <ProtectedRoute>
              <TwoFactorSetupPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute>
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit-logs"
          element={
            <ProtectedRoute>
              <AdminAuditLogsPage />
            </ProtectedRoute>
          }
        />

        {/* Catch all redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  )
}

export default App
