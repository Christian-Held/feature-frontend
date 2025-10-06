import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { Mock } from 'vitest'
import { vi } from 'vitest'

vi.mock('../../../features/admin/hooks', () => ({
  useAdminUsers: vi.fn(),
  useUpdateAdminUserRoles: vi.fn(),
  useLockAdminUser: vi.fn(),
  useUnlockAdminUser: vi.fn(),
  useResetAdminTwoFactor: vi.fn(),
  useResendAdminVerification: vi.fn(),
}))

import {
  useAdminUsers,
  useLockAdminUser,
  useResetAdminTwoFactor,
  useResendAdminVerification,
  useUnlockAdminUser,
  useUpdateAdminUserRoles,
} from '../../../features/admin/hooks'
import { ApiError } from '../../../lib/api'
import { queryClient } from '../../../lib/queryClient'
import { AdminUsersPage } from '../AdminUsersPage'

const useAdminUsersMock = useAdminUsers as unknown as Mock
const useUpdateAdminUserRolesMock = useUpdateAdminUserRoles as unknown as Mock
const useLockAdminUserMock = useLockAdminUser as unknown as Mock
const useUnlockAdminUserMock = useUnlockAdminUser as unknown as Mock
const useResetAdminTwoFactorMock = useResetAdminTwoFactor as unknown as Mock
const useResendAdminVerificationMock = useResendAdminVerification as unknown as Mock

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminUsersPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  queryClient.clear()
  useLockAdminUserMock.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  useUnlockAdminUserMock.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  useResetAdminTwoFactorMock.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false })
  useResendAdminVerificationMock.mockReturnValue({ mutateAsync: vi.fn().mockResolvedValue({ message: 'sent' }), isPending: false })
  useUpdateAdminUserRolesMock.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      id: 'u-1',
      email: 'user@example.com',
      status: 'ACTIVE',
      roles: ['ADMIN'],
      created_at: new Date().toISOString(),
      mfa_enabled: true,
      email_verified: true,
    }),
    isPending: false,
  })
})

const baseUsersResponse = {
  items: [
    {
      id: 'u-1',
      email: 'user@example.com',
      status: 'ACTIVE',
      roles: ['USER'],
      created_at: new Date().toISOString(),
      mfa_enabled: false,
      email_verified: true,
    },
    {
      id: 'u-2',
      email: 'disabled@example.com',
      status: 'DISABLED',
      roles: ['SUPPORT'],
      created_at: new Date().toISOString(),
      mfa_enabled: true,
      email_verified: false,
    },
  ],
  page: 1,
  page_size: 25,
  total: 2,
}

test('renders users table with filters and actions', () => {
  useAdminUsersMock.mockReturnValue({ data: baseUsersResponse, isLoading: false, isFetching: false })

  renderPage()

  expect(screen.getByLabelText(/search by email/i)).toBeInTheDocument()
  const table = screen.getByRole('table')
  expect(within(table).getByText('user@example.com')).toBeInTheDocument()
  expect(within(table).getByText('disabled@example.com')).toBeInTheDocument()
  expect(
    within(table).getAllByRole('button', { name: /lock|unlock|edit roles|reset 2fa|resend verification/i }),
  ).toHaveLength(8)
})

test('role edit dialog updates selection', async () => {
  const user = userEvent.setup()
  useAdminUsersMock.mockReturnValue({ data: baseUsersResponse, isLoading: false, isFetching: false })
  const mutateAsyncMock = vi.fn().mockResolvedValue({
    id: 'u-1',
    email: 'user@example.com',
    status: 'ACTIVE',
    roles: ['ADMIN', 'USER'],
    created_at: new Date().toISOString(),
    mfa_enabled: true,
    email_verified: true,
  })
  useUpdateAdminUserRolesMock.mockReturnValue({ mutateAsync: mutateAsyncMock, isPending: false })

  renderPage()

  await user.click(screen.getAllByRole('button', { name: /edit roles/i })[0])
  const modal = screen.getByRole('dialog')
  const adminCheckbox = within(modal).getByLabelText('ADMIN') as HTMLInputElement
  expect(adminCheckbox.checked).toBe(false)

  await user.click(adminCheckbox)
  await user.click(within(modal).getByRole('button', { name: /save/i }))

  expect(mutateAsyncMock).toHaveBeenCalledWith({ userId: 'u-1', roles: ['USER', 'ADMIN'] })
})

test('lock and unlock buttons reflect status', async () => {
  const user = userEvent.setup()
  useAdminUsersMock.mockReturnValue({ data: baseUsersResponse, isLoading: false, isFetching: false })
  const lockMutation = vi.fn().mockResolvedValue({})
  const unlockMutation = vi.fn().mockResolvedValue({})
  useLockAdminUserMock.mockReturnValue({ mutateAsync: lockMutation, isPending: false })
  useUnlockAdminUserMock.mockReturnValue({ mutateAsync: unlockMutation, isPending: false })

  renderPage()

  await user.click(screen.getAllByRole('button', { name: 'Lock' })[0])
  expect(lockMutation).toHaveBeenCalledWith('u-1')

  await user.click(screen.getByRole('button', { name: 'Unlock' }))
  expect(unlockMutation).toHaveBeenCalledWith('u-2')
})

test('shows unauthorized message when RBAC fails', () => {
  useAdminUsersMock.mockReturnValue({
    error: new ApiError('forbidden', 403),
    isLoading: false,
    isFetching: false,
  })

  renderPage()

  expect(screen.getByText('You don’t have permission to perform this action.')).toBeInTheDocument()
})
