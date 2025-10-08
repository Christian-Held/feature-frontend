/**
 * Billing API client
 */

import apiClient from '../../lib/api'

export interface StripeConfig {
  publishable_key: string
}

export interface CheckoutSessionCreate {
  plan_id: string
  success_url: string
  cancel_url: string
}

export interface CheckoutSessionResponse {
  session_id: string
  url: string
}

export interface PaymentIntentCreate {
  amount_cents: number
  currency?: string
  description?: string
}

export interface PaymentIntentResponse {
  client_secret: string
  payment_intent_id: string
}

export interface PaymentTransaction {
  id: string
  user_id: string
  subscription_id: string | null
  stripe_payment_intent_id: string | null
  stripe_charge_id: string | null
  stripe_customer_id: string | null
  amount_cents: number
  currency: string
  status: string
  payment_method: string | null
  payment_method_last4: string | null
  description: string | null
  failure_reason: string | null
  paid_at: string | null
  refunded_at: string | null
  created_at: string
  updated_at: string
}

export interface PaymentHistoryResponse {
  transactions: PaymentTransaction[]
  total: number
}

/**
 * Get Stripe publishable key
 */
export async function getStripeConfig(): Promise<StripeConfig> {
  const response = await apiClient.get<StripeConfig>('/v1/billing/config')
  return response
}

/**
 * Create a Stripe Checkout session
 */
export async function createCheckoutSession(
  data: CheckoutSessionCreate
): Promise<CheckoutSessionResponse> {
  const response = await apiClient.post<CheckoutSessionResponse>(
    '/v1/billing/checkout-session',
    data
  )
  return response
}

/**
 * Create a Stripe Payment Intent
 */
export async function createPaymentIntent(
  data: PaymentIntentCreate
): Promise<PaymentIntentResponse> {
  const response = await apiClient.post<PaymentIntentResponse>(
    '/v1/billing/payment-intent',
    data
  )
  return response
}

/**
 * Get payment history for the current user
 */
export async function getPaymentHistory(
  limit = 50,
  offset = 0
): Promise<PaymentHistoryResponse> {
  const response = await apiClient.get<PaymentHistoryResponse>(
    `/v1/billing/history?limit=${limit}&offset=${offset}`
  )
  return response
}
