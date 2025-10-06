import { QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { Mock } from 'vitest'
import { vi } from 'vitest'

vi.mock('../../../features/account/hooks', () => ({
  useAccountPlan: vi.fn(),
  useUpdateAccountPlan: vi.fn(),
}))

import { useAccountPlan, useUpdateAccountPlan } from '../../../features/account/hooks'
import { queryClient } from '../../../lib/queryClient'
import { BillingPage } from '../BillingPage'

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

const useAccountPlanMock = useAccountPlan as unknown as Mock
const useUpdateAccountPlanMock = useUpdateAccountPlan as unknown as Mock

beforeEach(() => {
  vi.resetAllMocks()
  queryClient.clear()
})

test('renders plans and updates selection', async () => {
  const user = userEvent.setup()
  useAccountPlanMock.mockReturnValue({
    data: { plan: 'FREE', name: 'Free', monthly_price_usd: '0.00' },
    isLoading: false,
  })

  const result = { mutate: vi.fn(), isPending: false, variables: undefined as any }
  result.mutate.mockImplementation((payload, options) => {
    result.variables = payload
    options?.onSuccess?.({ plan: payload.plan, name: payload.plan === 'PRO' ? 'Pro' : 'Free', monthly_price_usd: '0.00' })
  })
  useUpdateAccountPlanMock.mockReturnValue(result)

  renderWithProviders(<BillingPage />)

  expect(screen.getByText('Free')).toBeInTheDocument()
  const proCard = screen.getByRole('button', { name: /pro plan option/i })
  await user.click(proCard)

  expect(result.mutate).toHaveBeenCalledWith(
    { plan: 'PRO' },
    expect.objectContaining({
      onSuccess: expect.any(Function),
      onError: expect.any(Function),
    }),
  )
  expect(screen.getByText('Plan updated to Pro')).toBeInTheDocument()
})
