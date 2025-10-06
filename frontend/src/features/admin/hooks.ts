import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { AdminUsersQuery, AuditLogQuery } from '../../lib/api'
import {
  ADMIN_DEFAULT_SORT,
  exportAuditLogs,
  fetchAdminUsers,
  fetchAuditLogs,
  lockAdminUserAccount,
  resetAdminUserTwoFactor,
  resendAdminVerification,
  unlockAdminUserAccount,
  updateAdminUserRolesApi,
} from './api'

export function useAdminUsers(params: AdminUsersQuery) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => fetchAdminUsers({ sort: ADMIN_DEFAULT_SORT, ...params }),
    keepPreviousData: true,
  })
}

export function useUpdateAdminUserRoles() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateAdminUserRolesApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useLockAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: lockAdminUserAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useUnlockAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: unlockAdminUserAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useResetAdminTwoFactor() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: resetAdminUserTwoFactor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useResendAdminVerification() {
  return useMutation({
    mutationFn: resendAdminVerification,
  })
}

export function useAuditLogs(params: AuditLogQuery) {
  return useQuery({
    queryKey: ['admin', 'audit-logs', params],
    queryFn: () => fetchAuditLogs(params),
    keepPreviousData: true,
  })
}

export function useExportAuditLogs() {
  return useMutation({
    mutationFn: exportAuditLogs,
  })
}
