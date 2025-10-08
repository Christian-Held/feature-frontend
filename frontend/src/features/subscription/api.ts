/**
 * Subscription API client functions
 */

import { apiClient } from '../../lib/api'

export interface SubscriptionPlan {
  id: string
  name: string
  display_name: string
  description: string | null
  price_cents: number
  features: Record<string, any>
  rate_limit_multiplier: number
  max_jobs_per_month: number | null
  max_storage_mb: number | null
  max_api_calls_per_day: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserSubscription {
  id: string
  user_id: string
  plan_id: string
  status: string
  started_at: string
  expires_at: string | null
  stripe_subscription_id: string | null
  stripe_customer_id: string | null
  created_at: string
  updated_at: string
}

export interface UserUsage {
  id: string
  user_id: string
  period_start: string
  period_end: string
  api_calls: number
  jobs_created: number
  storage_used_mb: number
  compute_minutes: number
}

export interface SubscriptionResponse {
  subscription: UserSubscription | null
  plan: SubscriptionPlan
}

export interface UsageResponse {
  usage: UserUsage | null
  limits: {
    jobs: number | null
    storage: number | null
    api_calls: number | null
  }
}

export interface PlanListResponse {
  plans: SubscriptionPlan[]
}

export interface RateLimitInfo {
  base_limit: number
  multiplier: number
  effective_limit: number
  plan_name: string
}

/**
 * Get current user's subscription and plan
 */
export async function getMySubscription(): Promise<SubscriptionResponse> {
  const response = await apiClient.get<SubscriptionResponse>('/v1/subscription/me')
  return response
}

/**
 * Get current user's usage stats
 */
export async function getMyUsage(): Promise<UsageResponse> {
  const response = await apiClient.get<UsageResponse>('/v1/subscription/usage')
  return response
}

/**
 * Get all available subscription plans
 */
export async function getSubscriptionPlans(): Promise<PlanListResponse> {
  const response = await apiClient.get<PlanListResponse>('/v1/subscription/plans')
  return response
}

/**
 * Get current user's rate limit information
 */
export async function getMyRateLimits(): Promise<RateLimitInfo> {
  const response = await apiClient.get<RateLimitInfo>('/v1/subscription/rate-limits')
  return response
}
