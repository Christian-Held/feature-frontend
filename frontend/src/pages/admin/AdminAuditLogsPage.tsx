import { useMemo, useState } from 'react'

import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Spinner } from '../../components/ui/Spinner'
import type { AuditLogEntry, AuditLogQuery, PaginatedResponse } from '../../lib/api'
import { ApiError } from '../../lib/api'
import { useAuditLogs, useExportAuditLogs } from '../../features/admin/hooks'

const PAGE_SIZE = 50
const UNAUTHORIZED_COPY = 'You don’t have permission to perform this action.'

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function metadataPreview(metadata: Record<string, unknown> | null) {
  if (!metadata) return '—'
  const serialized = JSON.stringify(metadata)
  if (serialized.length <= 64) {
    return serialized
  }
  return `${serialized.slice(0, 64)}…`
}

function targetLabel(entry: AuditLogEntry) {
  if (!entry.target_type && !entry.target_id) {
    return '—'
  }
  return [entry.target_type, entry.target_id].filter(Boolean).join(' • ')
}

export function AdminAuditLogsPage() {
  const [actor, setActor] = useState('')
  const [action, setAction] = useState('')
  const [targetType, setTargetType] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [page, setPage] = useState(1)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const queryParams: AuditLogQuery = useMemo(
    () => ({
      actor: actor.trim() || undefined,
      action: action.trim() || undefined,
      target_type: targetType.trim() || undefined,
      from: fromDate ? new Date(fromDate).toISOString() : undefined,
      to: toDate ? new Date(`${toDate}T23:59:59`).toISOString() : undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [actor, action, targetType, fromDate, toDate, page],
  )

  const logsQuery = useAuditLogs(queryParams)
  const exportLogs = useExportAuditLogs()

  const data: PaginatedResponse<AuditLogEntry> | undefined = logsQuery.data
  const isLoading = logsQuery.isLoading
  const unauthorizedError = logsQuery.error instanceof ApiError && logsQuery.error.status === 403
  const total = data?.total ?? 0
  const totalPages = total > 0 ? Math.ceil(total / PAGE_SIZE) : 1

  const resetNotifications = () => {
    setStatusMessage(null)
    setErrorMessage(null)
  }

  const handleFilterSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    resetNotifications()
    setPage(1)
  }

  const handleExport = async () => {
    resetNotifications()
    try {
      const response = await exportLogs.mutateAsync(queryParams)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'admin-audit-logs.csv'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      setStatusMessage('Audit logs export started.')
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        setErrorMessage(UNAUTHORIZED_COPY)
      } else {
        setErrorMessage('Unable to export audit logs right now.')
      }
    }
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
        title="Admin – Audit Logs"
        description="Inspect platform activity, filter by actor, and export CSV reports."
      />
      <div className="flex-1 p-6">
        <form
          onSubmit={handleFilterSubmit}
          className="grid gap-4 rounded-2xl border border-slate-800/70 bg-slate-950/50 p-4 md:grid-cols-5"
        >
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-log-actor">
              Actor ID
            </label>
            <Input
              id="admin-log-actor"
              placeholder="admin user id"
              value={actor}
              onChange={(event) => setActor(event.target.value)}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-log-action">
              Action
            </label>
            <Input
              id="admin-log-action"
              placeholder="user_locked"
              value={action}
              onChange={(event) => setAction(event.target.value)}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-log-target">
              Target type
            </label>
            <Input
              id="admin-log-target"
              placeholder="user"
              value={targetType}
              onChange={(event) => setTargetType(event.target.value)}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-log-from">
              From date
            </label>
            <Input
              id="admin-log-from"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-300" htmlFor="admin-log-to">
              To date
            </label>
            <Input
              id="admin-log-to"
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
          <div className="md:col-span-5 flex justify-end gap-2">
            <Button type="submit" variant="primary">
              Apply filters
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={handleExport}
              disabled={exportLogs.isPending}
            >
              Export CSV
            </Button>
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
              <Spinner  />
            </div>
          ) : data && data.items.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-800 text-sm">
                <thead className="bg-slate-900/60 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left">Time</th>
                    <th className="px-4 py-3 text-left">Actor</th>
                    <th className="px-4 py-3 text-left">Action</th>
                    <th className="px-4 py-3 text-left">Target</th>
                    <th className="px-4 py-3 text-left">Metadata</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {data.items.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-900/60">
                      <td className="px-4 py-3 text-slate-200">{formatDate(entry.created_at)}</td>
                      <td className="px-4 py-3 text-slate-300">{entry.actor_user_id ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-300">{entry.action}</td>
                      <td className="px-4 py-3 text-slate-300">{targetLabel(entry)}</td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs">
                        {metadataPreview(entry.metadata)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-sm text-slate-300">No audit events found for the selected filters.</div>
          )}
          {data && data.items.length > 0 && (
            <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-300">
              <span>
                Page {page} of {totalPages}
                {logsQuery.isFetching && <span className="ml-2 text-xs text-slate-500">Updating…</span>}
              </span>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  
                  onClick={() => handlePageChange(-1)}
                  disabled={page <= 1}
                >
                  Previous
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  
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
    </AppShell>
  )
}

export default AdminAuditLogsPage
