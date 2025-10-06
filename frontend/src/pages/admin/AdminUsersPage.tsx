import { useMemo, useState } from 'react'

import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Modal } from '../../components/ui/Modal'
import { Spinner } from '../../components/ui/Spinner'
import type {
  AdminRole,
  AdminUserSort,
  AdminUserStatus,
  AdminUserSummary,
  PaginatedResponse,
} from '../../lib/api'
import { ApiError } from '../../lib/api'
import {
  useAdminUsers,
  useLockAdminUser,
  useResetAdminTwoFactor,
  useResendAdminVerification,
  useUnlockAdminUser,
  useUpdateAdminUserRoles,
} from '../../features/admin/hooks'

const ROLE_OPTIONS: AdminRole[] = ['ADMIN', 'USER', 'BILLING_ADMIN', 'SUPPORT']
const STATUS_OPTIONS: Array<AdminUserStatus | 'ALL'> = ['ALL', 'ACTIVE', 'UNVERIFIED', 'DISABLED']
const SORT_OPTIONS: Array<{ value: AdminUserSort; label: string }> = [
  { value: 'created_at_desc', label: 'Newest first' },
  { value: 'created_at_asc', label: 'Oldest first' },
]
const PAGE_SIZE = 25
const UNAUTHORIZED_COPY = 'You don’t have permission to perform this action.'

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function RolesCell({ roles }: { roles: AdminRole[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {roles.map((role) => (
        <Badge key={role} variant="secondary">
          {role}
        </Badge>
      ))}
    </div>
  )
}

export function AdminUsersPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [queryEmail, setQueryEmail] = useState('')
  const [status, setStatus] = useState<AdminUserStatus | 'ALL'>('ALL')
  const [role, setRole] = useState<AdminRole | 'ALL'>('ALL')
  const [sort, setSort] = useState<AdminUserSort>('created_at_desc')
  const [page, setPage] = useState(1)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [roleDialogUser, setRoleDialogUser] = useState<AdminUserSummary | null>(null)
  const [roleSelections, setRoleSelections] = useState<AdminRole[]>([])

  const queryParams = useMemo(
    () => ({
      q: queryEmail || undefined,
      status: status !== 'ALL' ? status : undefined,
      role: role !== 'ALL' ? role : undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    }),
    [queryEmail, status, role, sort, page],
  )

  const usersQuery = useAdminUsers(queryParams)
  const updateRoles = useUpdateAdminUserRoles()
  const lockUser = useLockAdminUser()
  const unlockUser = useUnlockAdminUser()
  const resetTwoFactor = useResetAdminTwoFactor()
  const resendVerification = useResendAdminVerification()

  const data: PaginatedResponse<AdminUserSummary> | undefined = usersQuery.data
  const isLoading = usersQuery.isLoading
  const isFetching = usersQuery.isFetching
  const total = data?.total ?? 0
  const totalPages = total > 0 ? Math.ceil(total / PAGE_SIZE) : 1
  const unauthorizedError = usersQuery.error instanceof ApiError && usersQuery.error.status === 403

  const handleSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPage(1)
    setQueryEmail(searchTerm.trim())
  }

  const resetNotifications = () => {
    setStatusMessage(null)
    setErrorMessage(null)
  }

  const handleRoleDialogOpen = (user: AdminUserSummary) => {
    setRoleDialogUser(user)
    setRoleSelections([...user.roles])
    resetNotifications()
  }

  const handleRoleToggle = (roleName: AdminRole) => {
    setRoleSelections((prev) =>
      prev.includes(roleName) ? prev.filter((item) => item !== roleName) : [...prev, roleName],
    )
  }

  const handleRoleSave = async () => {
    if (!roleDialogUser) return
    try {
      resetNotifications()
      const updated = await updateRoles.mutateAsync({ userId: roleDialogUser.id, roles: roleSelections })
      setStatusMessage(`Roles updated for ${updated.email}.`)
      setRoleDialogUser(null)
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.status === 403 ? UNAUTHORIZED_COPY : error.message)
      } else {
        setErrorMessage('Unable to update roles right now.')
      }
    }
  }

  const performAction = async (
    action: 'lock' | 'unlock' | 'reset' | 'resend',
    user: AdminUserSummary,
  ) => {
    resetNotifications()
    try {
      if (action === 'lock') {
        await lockUser.mutateAsync(user.id)
        setStatusMessage(`User ${user.email} locked.`)
      } else if (action === 'unlock') {
        await unlockUser.mutateAsync(user.id)
        setStatusMessage(`User ${user.email} unlocked.`)
      } else if (action === 'reset') {
        await resetTwoFactor.mutateAsync(user.id)
        setStatusMessage(`Two-factor authentication reset for ${user.email}.`)
      } else if (action === 'resend') {
        const response = await resendVerification.mutateAsync(user.id)
        setStatusMessage(response.message)
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          setErrorMessage(UNAUTHORIZED_COPY)
        } else {
          setErrorMessage(error.message)
        }
      } else {
        setErrorMessage('An unexpected error occurred. Please try again.')
      }
    }
  }

  const handleStatusChange = (value: AdminUserStatus | 'ALL') => {
    setStatus(value)
    setPage(1)
  }

  const handleRoleFilterChange = (value: AdminRole | 'ALL') => {
    setRole(value)
    setPage(1)
  }

  const handleSortChange = (value: AdminUserSort) => {
    setSort(value)
    setPage(1)
  }

  const handlePageChange = (direction: -1 | 1) => {
    setPage((prev) => {
      const next = prev + direction
      if (next < 1) return 1
      if (data && next > totalPages) return totalPages
      return next
    })
  }

  return (
    <AppShell>
      <Header
        title="Admin – Users"
        description="Manage user access, enforce MFA, and resend verification emails."
      />
      <div className="flex-1 p-6">
        <form
          onSubmit={handleSearch}
          className="grid gap-4 rounded-2xl border border-slate-800/70 bg-slate-950/50 p-4 md:grid-cols-4"
        >
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-user-search">
              Search by email
            </label>
            <div className="flex gap-2">
              <Input
                id="admin-user-search"
                placeholder="user@example.com"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
              <Button type="submit" variant="primary">
                Search
              </Button>
            </div>
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-user-status">
              Status
            </label>
            <select
              id="admin-user-status"
              value={status}
              onChange={(event) => handleStatusChange(event.target.value as AdminUserStatus | 'ALL')}
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'ALL' ? 'All statuses' : option}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-user-role">
              Role
            </label>
            <select
              id="admin-user-role"
              value={role}
              onChange={(event) => handleRoleFilterChange(event.target.value as AdminRole | 'ALL')}
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            >
              <option value="ALL">All roles</option>
              {ROLE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-user-sort">
              Sort
            </label>
            <select
              id="admin-user-sort"
              value={sort}
              onChange={(event) => handleSortChange(event.target.value as AdminUserSort)}
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2 text-sm text-slate-100"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </form>

        <div className="mt-4 space-y-3">
          {statusMessage && (
            <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              {statusMessage}
            </div>
          )}
          {errorMessage && (
            <div className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {errorMessage}
            </div>
          )}
        </div>

        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800/70 bg-slate-950/60">
          {unauthorizedError ? (
            <div className="p-6 text-sm text-red-300">{UNAUTHORIZED_COPY}</div>
          ) : isLoading ? (
            <div className="flex min-h-[280px] items-center justify-center">
              <Spinner size="lg" />
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-800 text-sm">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left">Email</th>
                    <th className="px-4 py-3 text-left">Status</th>
                    <th className="px-4 py-3 text-left">Roles</th>
                    <th className="px-4 py-3 text-left">Created</th>
                    <th className="px-4 py-3 text-left">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {data.items.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-900/60">
                      <td className="px-4 py-3 font-medium text-slate-100">{user.email}</td>
                      <td className="px-4 py-3 text-slate-300">{user.status}</td>
                      <td className="px-4 py-3 text-slate-300">
                        <RolesCell roles={user.roles} />
                      </td>
                      <td className="px-4 py-3 text-slate-300">{formatDate(user.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant={user.status === 'DISABLED' ? 'primary' : 'secondary'}
                            onClick={() =>
                              performAction(user.status === 'DISABLED' ? 'unlock' : 'lock', user)
                            }
                            disabled={lockUser.isPending || unlockUser.isPending}
                          >
                            {user.status === 'DISABLED' ? 'Unlock' : 'Lock'}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => handleRoleDialogOpen(user)}
                          >
                            Edit Roles
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => performAction('reset', user)}
                            disabled={resetTwoFactor.isPending}
                          >
                            Reset 2FA
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="secondary"
                            onClick={() => performAction('resend', user)}
                            disabled={resendVerification.isPending || user.status !== 'UNVERIFIED'}
                          >
                            Resend Verification
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-sm text-slate-300">No users found for the selected filters.</div>
          )}
          {data && data.items.length > 0 && (
            <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-300">
              <span>
                Page {page} of {totalPages}
                {isFetching && <span className="ml-2 text-xs text-slate-500">Updating…</span>}
              </span>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(-1)}
                  disabled={page <= 1}
                >
                  Previous
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => handlePageChange(1)}
                  disabled={page >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      <Modal
        open={Boolean(roleDialogUser)}
        title={roleDialogUser ? `Edit roles – ${roleDialogUser.email}` : 'Edit roles'}
        onClose={() => setRoleDialogUser(null)}
        footer={
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setRoleDialogUser(null)}>
              Cancel
            </Button>
            <Button type="button" variant="primary" onClick={handleRoleSave} disabled={updateRoles.isPending}>
              Save
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          {ROLE_OPTIONS.map((roleName) => {
            const checked = roleSelections.includes(roleName)
            return (
              <label key={roleName} className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
                  checked={checked}
                  onChange={() => handleRoleToggle(roleName)}
                />
                <span className="text-slate-200">{roleName}</span>
              </label>
            )
          })}
          {roleDialogUser?.email_verified ? (
            <p className="rounded-lg bg-slate-900/70 p-3 text-xs text-slate-400">
              MFA requirement: {roleDialogUser.mfa_enabled ? 'Enabled' : 'Not enabled'}
            </p>
          ) : (
            <p className="rounded-lg bg-amber-500/10 p-3 text-xs text-amber-200">
              This user has not verified their email yet.
            </p>
          )}
        </div>
      </Modal>
    </AppShell>
  )
}

export default AdminUsersPage
