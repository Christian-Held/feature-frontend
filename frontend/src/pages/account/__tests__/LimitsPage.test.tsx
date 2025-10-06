import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { Mock } from 'vitest'
import { vi } from 'vitest'

vi.mock('../../../features/account/hooks', () => ({
  useAccountLimits: vi.fn(),
  useUpdateAccountLimits: vi.fn(),
}))

import { useAccountLimits, useUpdateAccountLimits } from '../../../features/account/hooks'
import { setSpendWarning } from '../../../features/account/store'
import { queryClient } from '../../../lib/queryClient'
import { CAP_WARNING_MESSAGE } from '../../../features/account/constants'
import { LimitsPage } from '../LimitsPage'
import { ApiError } from '../../../lib/api'

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

const useAccountLimitsMock = useAccountLimits as unknown as Mock
const useUpdateAccountLimitsMock = useUpdateAccountLimits as unknown as Mock

beforeEach(() => {
  vi.resetAllMocks()
  queryClient.clear()
})

test('renders limits and submits updates', async () => {
  const user = userEvent.setup()
  useAccountLimitsMock.mockReturnValue({
    data: {
      monthly_cap_usd: '120.00',
      hard_stop: false,
      usage_usd: '45.00',
      remaining_usd: '75.00',
      cap_reached: false,
    },
    isLoading: false,
  })
  const result = { mutate: vi.fn(), isPending: false }
  result.mutate.mockImplementation((payload, options) => {
    options?.onSuccess?.({
      monthly_cap_usd: '200.00',
      hard_stop: true,
      usage_usd: '45.00',
      remaining_usd: '155.00',
      cap_reached: false,
    })
  })
  useUpdateAccountLimitsMock.mockReturnValue(result)

  renderWithProviders(<LimitsPage />)

  const input = screen.getByLabelText(/monthly spending cap/i)
  await user.clear(input)
  await user.type(input, '200')
  await user.click(screen.getByRole('checkbox'))
  await user.click(screen.getByRole('button', { name: /save limits/i }))

  expect(result.mutate).toHaveBeenCalledWith(
    { monthly_cap_usd: '200', hard_stop: true },
    expect.any(Object),
  )
  expect(screen.getByText('Spending limits updated successfully.')).toBeInTheDocument()
})

test('shows exact warning copy when cap reached error occurs', async () => {
  const user = userEvent.setup()
  useAccountLimitsMock.mockReturnValue({
    data: {
      monthly_cap_usd: '50.00',
      hard_stop: true,
      usage_usd: '50.00',
      remaining_usd: '0.00',
      cap_reached: true,
    },
    isLoading: false,
  })
  const result = { mutate: vi.fn(), isPending: false }
  result.mutate.mockImplementation((_payload, options) => {
    options?.onError?.(new ApiError(CAP_WARNING_MESSAGE, 402))
  })
  useUpdateAccountLimitsMock.mockReturnValue(result)

  renderWithProviders(<LimitsPage />)

  await user.click(screen.getByRole('button', { name: /save limits/i }))
  expect(screen.getByText(CAP_WARNING_MESSAGE)).toBeInTheDocument()
})

test('renders global banner when warning state active', () => {
  useAccountLimitsMock.mockReturnValue({
    data: {
      monthly_cap_usd: '10.00',
      hard_stop: false,
      usage_usd: '10.00',
      remaining_usd: '0.00',
      cap_reached: true,
    },
    isLoading: false,
  })
  useUpdateAccountLimitsMock.mockReturnValue({ mutate: vi.fn(), isPending: false })

  setSpendWarning(CAP_WARNING_MESSAGE)
  renderWithProviders(<LimitsPage />)
  expect(screen.getByText(/Spend Limit Warning/i)).toBeInTheDocument()
  expect(screen.getByText(CAP_WARNING_MESSAGE)).toBeInTheDocument()
})
