import { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { BillingPage } from './pages/account/BillingPage'
import { LimitsPage } from './pages/account/LimitsPage'
import { SettingsPage } from './pages/SettingsPage'
import { AdminUsersPage } from './pages/admin/AdminUsersPage'
import { AdminAuditLogsPage } from './pages/admin/AdminAuditLogsPage'
import { Spinner } from './components/ui/Spinner'

export function App() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
          <Spinner size="lg" />
        </div>
      }
    >
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/account/billing" element={<BillingPage />} />
        <Route path="/account/limits" element={<LimitsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="/admin/audit-logs" element={<AdminAuditLogsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default App
