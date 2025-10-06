import {
  AccountLimitsResponse,
  AccountLimitsUpdateRequest,
  AccountPlanResponse,
  AccountPlanUpdateRequest,
  ApiError,
  apiClient,
} from '../../lib/api'
import { CAP_WARNING_MESSAGE } from './constants'
import { clearSpendWarning, setSpendWarning } from './store'

function handleWarning(flag?: string | null, capReached?: boolean) {
  if (flag === 'cap_reached' || capReached) {
    setSpendWarning(CAP_WARNING_MESSAGE)
  } else if (!capReached) {
    clearSpendWarning()
  }
}

function normalizeCap(value: string | number): string {
  const numeric = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(numeric) || numeric < 0) {
    return '0.00'
  }
  return numeric.toFixed(2)
}

export async function fetchAccountPlan(): Promise<AccountPlanResponse> {
  const { data, warning } = await apiClient.getAccountPlan()
  handleWarning(warning)
  return data
}

export async function updateAccountPlan(payload: AccountPlanUpdateRequest): Promise<AccountPlanResponse> {
  const { data, warning } = await apiClient.updateAccountPlan(payload)
  handleWarning(warning)
  return data
}

export async function fetchAccountLimits(): Promise<AccountLimitsResponse> {
  const { data, warning } = await apiClient.getAccountLimits()
  handleWarning(warning, data.cap_reached)
  return data
}

export async function updateAccountLimits(
  payload: AccountLimitsUpdateRequest,
): Promise<AccountLimitsResponse> {
  try {
    const { data, warning } = await apiClient.updateAccountLimits({
      ...payload,
      monthly_cap_usd: normalizeCap(payload.monthly_cap_usd),
    })
    handleWarning(warning, data.cap_reached)
    return data
  } catch (error) {
    if (error instanceof ApiError && error.status === 402) {
      setSpendWarning(CAP_WARNING_MESSAGE)
    }
    throw error
  }
}
