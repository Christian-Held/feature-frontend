/**
 * React Query hooks for subscription features
 */

import { useQuery } from '@tanstack/react-query'
import { getMySubscription, getMyUsage, getSubscriptionPlans, getMyRateLimits } from './api'

/**
 * Hook to fetch current user's subscription
 */
export function useSubscription() {
  return useQuery({
    queryKey: ['subscription', 'me'],
    queryFn: getMySubscription,
    staleTime: 30000, // 30 seconds
  })
}

/**
 * Hook to fetch current user's usage stats
 */
export function useUsage() {
  return useQuery({
    queryKey: ['subscription', 'usage'],
    queryFn: getMyUsage,
    staleTime: 10000, // 10 seconds
  })
}

/**
 * Hook to fetch all available subscription plans
 */
export function usePlans() {
  return useQuery({
    queryKey: ['subscription', 'plans'],
    queryFn: getSubscriptionPlans,
    staleTime: 60000, // 1 minute
  })
}

/**
 * Hook to fetch current user's rate limit info
 */
export function useRateLimits() {
  return useQuery({
    queryKey: ['subscription', 'rate-limits'],
    queryFn: getMyRateLimits,
    staleTime: 30000, // 30 seconds
  })
}
