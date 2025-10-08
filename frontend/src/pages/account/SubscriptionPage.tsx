import { useState } from 'react'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Spinner } from '../../components/ui/Spinner'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { useSubscription, useUsage, usePlans, useRateLimits } from '../../features/subscription/hooks'
import { useCreateCheckoutSession } from '../../features/billing/hooks'

function formatBytes(mb: number): string {
  if (mb < 1024) return `${mb.toFixed(0)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`
}

export function SubscriptionPage() {
  const [upgradingPlanId, setUpgradingPlanId] = useState<string | null>(null)
  const { data: subscriptionData, isLoading: isLoadingSub } = useSubscription()
  const { data: usageData, isLoading: isLoadingUsage } = useUsage()
  const { data: plansData, isLoading: isLoadingPlans } = usePlans()
  const { data: rateLimitData, isLoading: isLoadingRateLimits } = useRateLimits()
  const createCheckoutSession = useCreateCheckoutSession()

  const isLoading = isLoadingSub || isLoadingUsage || isLoadingPlans

  const handleUpgrade = async (planId: string) => {
    setUpgradingPlanId(planId)
    try {
      const result = await createCheckoutSession.mutateAsync({
        plan_id: planId,
        success_url: `${window.location.origin}/account/subscription?success=true`,
        cancel_url: `${window.location.origin}/account/subscription?canceled=true`,
      })
      // Redirect to Stripe Checkout
      window.location.href = result.url
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      setUpgradingPlanId(null)
    }
  }

  if (isLoading) {
    return (
      <AppShell>
        <Header title="Subscription" description="Manage your subscription plan and usage" />
        <div className="flex min-h-[400px] items-center justify-center p-6">
          <Spinner size="lg" />
        </div>
      </AppShell>
    )
  }

  const plan = subscriptionData?.plan
  const subscription = subscriptionData?.subscription
  const usage = usageData?.usage
  const limits = usageData?.limits
  const plans = plansData?.plans || []

  return (
    <AppShell>
      <Header title="Subscription" description="Manage your subscription plan and usage" />

      <div className="flex-1 space-y-6 p-6">
        {/* Current Plan */}
        <Card>
          <div className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{plan?.display_name || 'Free Plan'}</h2>
                <p className="mt-1 text-sm text-slate-400">{plan?.description || 'Basic features'}</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-white">
                  {plan ? formatPrice(plan.price_cents) : '$0'}
                  <span className="text-base font-normal text-slate-400">/month</span>
                </div>
                {subscription && (
                  <Badge variant={subscription.status === 'active' ? 'success' : 'default'} className="mt-2">
                    {subscription.status}
                  </Badge>
                )}
              </div>
            </div>

            {subscription?.expires_at && (
              <div className="mt-4 rounded-lg bg-slate-900/50 p-3">
                <p className="text-sm text-slate-300">
                  {subscription.status === 'active' ? 'Renews' : 'Expires'} on{' '}
                  {new Date(subscription.expires_at).toLocaleDateString()}
                </p>
              </div>
            )}

            {plan && (
              <div className="mt-6 space-y-2">
                <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Plan Features</h3>
                <ul className="space-y-2">
                  <li className="flex items-center gap-2 text-sm text-slate-300">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                    Rate Limit Multiplier: {plan.rate_limit_multiplier}x
                  </li>
                  {Object.entries(plan.features || {}).map(([key, value]) => (
                    <li key={key} className="flex items-center gap-2 text-sm text-slate-300">
                      <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                      {key.replace(/_/g, ' ')}: {value === true ? 'Yes' : value === false ? 'No' : String(value)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>

        {/* Rate Limits */}
        {rateLimitData && (
          <Card>
            <div className="p-6">
              <h2 className="mb-4 text-xl font-bold text-white">API Rate Limits</h2>

              <div className="grid gap-4 md:grid-cols-3">
                {/* Base Limit */}
                <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                  <div className="text-sm font-medium text-slate-400">Base Limit</div>
                  <div className="mt-2 text-2xl font-bold text-white">
                    {rateLimitData.base_limit}
                    <span className="text-sm font-normal text-slate-400"> req/min</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">Standard rate for all users</p>
                </div>

                {/* Multiplier */}
                <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                  <div className="text-sm font-medium text-slate-400">Plan Multiplier</div>
                  <div className="mt-2 text-2xl font-bold text-sky-400">
                    {rateLimitData.multiplier}x
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {rateLimitData.plan_name.charAt(0).toUpperCase() + rateLimitData.plan_name.slice(1)} plan bonus
                  </p>
                </div>

                {/* Effective Limit */}
                <div className="rounded-lg border border-sky-500/50 bg-sky-500/10 p-4">
                  <div className="text-sm font-medium text-sky-300">Your Effective Limit</div>
                  <div className="mt-2 text-2xl font-bold text-white">
                    {rateLimitData.effective_limit}
                    <span className="text-sm font-normal text-slate-400"> req/min</span>
                  </div>
                  <p className="mt-1 text-xs text-sky-300/80">
                    {rateLimitData.base_limit} × {rateLimitData.multiplier}
                  </p>
                </div>
              </div>

              <div className="mt-4 rounded-lg bg-slate-900/50 p-3">
                <p className="text-sm text-slate-400">
                  Your API requests are limited to <strong className="text-white">{rateLimitData.effective_limit} requests per minute</strong>.
                  Upgrade your plan for higher rate limits.
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* Usage Stats */}
        <Card>
          <div className="p-6">
            <h2 className="mb-6 text-xl font-bold text-white">Current Usage</h2>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {/* Jobs */}
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                <div className="text-sm font-medium text-slate-400">Jobs Created</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-white">{usage?.jobs_created || 0}</div>
                  {limits?.jobs !== null && limits?.jobs !== undefined && (
                    <div className="text-sm text-slate-400">/ {limits.jobs}</div>
                  )}
                  {limits?.jobs === null && (
                    <div className="text-sm text-emerald-400">/ unlimited</div>
                  )}
                </div>
                {limits?.jobs !== null && limits?.jobs !== undefined && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-sky-500"
                      style={{
                        width: `${Math.min(((usage?.jobs_created || 0) / limits.jobs) * 100, 100)}%`,
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Storage */}
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                <div className="text-sm font-medium text-slate-400">Storage Used</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-white">{formatBytes(usage?.storage_used_mb || 0)}</div>
                  {limits?.storage !== null && limits?.storage !== undefined && (
                    <div className="text-sm text-slate-400">/ {formatBytes(limits.storage)}</div>
                  )}
                  {limits?.storage === null && (
                    <div className="text-sm text-emerald-400">/ unlimited</div>
                  )}
                </div>
                {limits?.storage !== null && limits?.storage !== undefined && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-sky-500"
                      style={{
                        width: `${Math.min(((usage?.storage_used_mb || 0) / limits.storage) * 100, 100)}%`,
                      }}
                    />
                  </div>
                )}
              </div>

              {/* API Calls */}
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                <div className="text-sm font-medium text-slate-400">API Calls (Today)</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-white">{usage?.api_calls || 0}</div>
                  {limits?.api_calls !== null && limits?.api_calls !== undefined && (
                    <div className="text-sm text-slate-400">/ {limits.api_calls}</div>
                  )}
                  {limits?.api_calls === null && (
                    <div className="text-sm text-emerald-400">/ unlimited</div>
                  )}
                </div>
                {limits?.api_calls !== null && limits?.api_calls !== undefined && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-sky-500"
                      style={{
                        width: `${Math.min(((usage?.api_calls || 0) / limits.api_calls) * 100, 100)}%`,
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Compute Minutes */}
              <div className="rounded-lg border border-slate-800/70 bg-slate-950/50 p-4">
                <div className="text-sm font-medium text-slate-400">Compute Minutes</div>
                <div className="mt-2 flex items-baseline gap-2">
                  <div className="text-2xl font-bold text-white">{usage?.compute_minutes || 0}</div>
                  <div className="text-sm text-slate-400">min</div>
                </div>
              </div>
            </div>

            {usage && (
              <div className="mt-4 text-sm text-slate-400">
                Current period: {new Date(usage.period_start).toLocaleDateString()} -{' '}
                {new Date(usage.period_end).toLocaleDateString()}
              </div>
            )}
          </div>
        </Card>

        {/* Available Plans */}
        <Card>
          <div className="p-6">
            <h2 className="mb-6 text-xl font-bold text-white">Available Plans</h2>

            <div className="grid gap-4 md:grid-cols-3">
              {plans.map((availablePlan) => {
                const isCurrentPlan = availablePlan.id === plan?.id
                return (
                  <div
                    key={availablePlan.id}
                    className={`rounded-lg border p-4 ${
                      isCurrentPlan
                        ? 'border-sky-500 bg-sky-500/10'
                        : 'border-slate-800/70 bg-slate-950/50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-white">{availablePlan.display_name}</h3>
                        <p className="mt-1 text-2xl font-bold text-white">
                          {formatPrice(availablePlan.price_cents)}
                          <span className="text-sm font-normal text-slate-400">/mo</span>
                        </p>
                      </div>
                      {isCurrentPlan && (
                        <Badge variant="success">Current</Badge>
                      )}
                    </div>

                    <ul className="mt-4 space-y-2 text-sm text-slate-300">
                      {availablePlan.max_jobs_per_month && (
                        <li className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-sky-400" />
                          {availablePlan.max_jobs_per_month} jobs/month
                        </li>
                      )}
                      {!availablePlan.max_jobs_per_month && (
                        <li className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-emerald-400" />
                          Unlimited jobs
                        </li>
                      )}
                      {availablePlan.max_storage_mb && (
                        <li className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-sky-400" />
                          {formatBytes(availablePlan.max_storage_mb)} storage
                        </li>
                      )}
                      {availablePlan.max_api_calls_per_day && (
                        <li className="flex items-center gap-2">
                          <span className="h-1 w-1 rounded-full bg-sky-400" />
                          {availablePlan.max_api_calls_per_day.toLocaleString()} API calls/day
                        </li>
                      )}
                      <li className="flex items-center gap-2">
                        <span className="h-1 w-1 rounded-full bg-sky-400" />
                        {availablePlan.rate_limit_multiplier}x rate limits
                      </li>
                    </ul>

                    {!isCurrentPlan && availablePlan.price_cents > 0 && (
                      <button
                        onClick={() => handleUpgrade(availablePlan.id)}
                        disabled={upgradingPlanId !== null}
                        className="mt-4 w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {upgradingPlanId === availablePlan.id ? (
                          <span className="flex items-center justify-center gap-2">
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                            Processing...
                          </span>
                        ) : (
                          'Upgrade Now'
                        )}
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  )
}

export default SubscriptionPage
