import { useQuery, useQueryClient } from '@tanstack/react-query'

import { queryClient } from '../../lib/queryClient'
import { CAP_WARNING_MESSAGE } from './constants'

export type SpendWarningState = {
  active: boolean
  message: string
}

const SPEND_WARNING_KEY = ['account', 'spend-warning'] as const
const DEFAULT_WARNING: SpendWarningState = { active: false, message: '' }

export function getSpendWarningState(): SpendWarningState {
  return (queryClient.getQueryData(SPEND_WARNING_KEY) as SpendWarningState | undefined) ?? DEFAULT_WARNING
}

export function setSpendWarning(message: string = CAP_WARNING_MESSAGE) {
  queryClient.setQueryData<SpendWarningState>(SPEND_WARNING_KEY, { active: true, message })
}

export function clearSpendWarning() {
  queryClient.setQueryData<SpendWarningState>(SPEND_WARNING_KEY, DEFAULT_WARNING)
}

export function useSpendWarning() {
  const client = useQueryClient()
  return useQuery({
    queryKey: SPEND_WARNING_KEY,
    queryFn: () => getSpendWarningState(),
    initialData: () => getSpendWarningState(),
    staleTime: Infinity,
    gcTime: Infinity,
    meta: { source: 'spend-warning' },
    onSuccess: (data) => {
      client.setQueryData(SPEND_WARNING_KEY, data)
    },
  })
}
