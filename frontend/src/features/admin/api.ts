import type {
  AdminRole,
  AdminUserActionResponse,
  AdminUserSort,
  AdminUserSummary,
  AdminUsersQuery,
  AuditLogEntry,
  AuditLogQuery,
  PaginatedResponse,
  ResendVerificationActionResponse,
} from '../../lib/api'
import { apiClient } from '../../lib/api'

export async function fetchAdminUsers(params: AdminUsersQuery): Promise<PaginatedResponse<AdminUserSummary>> {
  return apiClient.listAdminUsers(params)
}

export async function updateAdminUserRolesApi({
  userId,
  roles,
}: {
  userId: string
  roles: AdminRole[]
}): Promise<AdminUserSummary> {
  return apiClient.updateAdminUserRoles(userId, roles)
}

export async function lockAdminUserAccount(userId: string): Promise<AdminUserActionResponse> {
  return apiClient.lockAdminUser(userId)
}

export async function unlockAdminUserAccount(userId: string): Promise<AdminUserActionResponse> {
  return apiClient.unlockAdminUser(userId)
}

export async function resetAdminUserTwoFactor(userId: string): Promise<AdminUserActionResponse> {
  return apiClient.resetAdminUserTwoFactor(userId)
}

export async function resendAdminVerification(userId: string): Promise<ResendVerificationActionResponse> {
  return apiClient.resendAdminVerification(userId)
}

export async function fetchAuditLogs(params: AuditLogQuery): Promise<PaginatedResponse<AuditLogEntry>> {
  return apiClient.listAuditLogs(params)
}

export async function exportAuditLogs(params: AuditLogQuery): Promise<Response> {
  return apiClient.exportAuditLogsCsv(params)
}

export const ADMIN_DEFAULT_SORT: AdminUserSort = 'created_at_desc'
