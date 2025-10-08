/**
 * React Query hooks for billing operations
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createCheckoutSession,
  createPaymentIntent,
  getPaymentHistory,
  getStripeConfig,
  type CheckoutSessionCreate,
  type PaymentIntentCreate,
} from './api'

/**
 * Hook to get Stripe configuration
 */
export function useStripeConfig() {
  return useQuery({
    queryKey: ['billing', 'config'],
    queryFn: getStripeConfig,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to create a checkout session
 */
export function useCreateCheckoutSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CheckoutSessionCreate) => createCheckoutSession(data),
    onSuccess: () => {
      // Invalidate subscription data as it may change after payment
      queryClient.invalidateQueries({ queryKey: ['subscription'] })
    },
  })
}

/**
 * Hook to create a payment intent
 */
export function useCreatePaymentIntent() {
  return useMutation({
    mutationFn: (data: PaymentIntentCreate) => createPaymentIntent(data),
  })
}

/**
 * Hook to get payment history
 */
export function usePaymentHistory(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['billing', 'history', limit, offset],
    queryFn: () => getPaymentHistory(limit, offset),
    staleTime: 30000, // 30 seconds
  })
}
