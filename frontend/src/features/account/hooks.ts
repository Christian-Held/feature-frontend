import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  fetchAccountLimits,
  fetchAccountPlan,
  updateAccountLimits,
  updateAccountPlan,
} from './api'
import { AccountLimitsResponse, AccountPlanResponse } from '../../lib/api'

export function useAccountPlan() {
  return useQuery<AccountPlanResponse>({
    queryKey: ['account', 'plan'],
    queryFn: fetchAccountPlan,
  })
}

export function useUpdateAccountPlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateAccountPlan,
    onSuccess: (data) => {
      queryClient.setQueryData(['account', 'plan'], data)
    },
  })
}

export function useAccountLimits() {
  return useQuery<AccountLimitsResponse>({
    queryKey: ['account', 'limits'],
    queryFn: fetchAccountLimits,
  })
}

export function useUpdateAccountLimits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateAccountLimits,
    onSuccess: (data) => {
      queryClient.setQueryData(['account', 'limits'], data)
    },
  })
}
