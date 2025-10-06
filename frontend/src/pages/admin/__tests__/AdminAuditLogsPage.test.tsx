import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { Mock } from 'vitest'
import { vi } from 'vitest'

vi.mock('../../../features/admin/hooks', () => ({
  useAuditLogs: vi.fn(),
  useExportAuditLogs: vi.fn(),
}))

import { useAuditLogs, useExportAuditLogs } from '../../../features/admin/hooks'
import { ApiError } from '../../../lib/api'
import { queryClient } from '../../../lib/queryClient'
import { AdminAuditLogsPage } from '../AdminAuditLogsPage'

const useAuditLogsMock = useAuditLogs as unknown as Mock
const useExportAuditLogsMock = useExportAuditLogs as unknown as Mock

const baseAuditResponse = {
  items: [
    {
      id: 'log-1',
      actor_user_id: 'admin-1',
      action: 'user_locked',
      target_type: 'user',
      target_id: 'target-1',
      ip: '127.0.0.1',
      user_agent: 'agent',
      metadata: { email_hash: 'abc123' },
      created_at: new Date().toISOString(),
    },
  ],
  page: 1,
  page_size: 50,
  total: 1,
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminAuditLogsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  queryClient.clear()
  useAuditLogsMock.mockReturnValue({ data: baseAuditResponse, isLoading: false, isFetching: false })
  useExportAuditLogsMock.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue(new Response('id\n')), isPending: false })
})

test('renders audit logs table and filters', () => {
  renderPage()

  expect(screen.getByLabelText(/actor id/i)).toBeInTheDocument()
  expect(screen.getByText('user_locked')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /export csv/i })).toBeInTheDocument()
})

test('export button triggers download', async () => {
  const user = userEvent.setup()
  renderPage()

  const exportButton = screen.getByRole('button', { name: /export csv/i })
  await user.click(exportButton)

  const mutateAsync = useExportAuditLogsMock.mock.results[0].value.mutateAsync as Mock
  expect(mutateAsync).toHaveBeenCalled()
})

test('shows unauthorized message on forbidden response', () => {
  useAuditLogsMock.mockReturnValue({ error: new ApiError('nope', 403), isLoading: false, isFetching: false })

  renderPage()

  expect(screen.getByText('You don’t have permission to perform this action.')).toBeInTheDocument()
})
