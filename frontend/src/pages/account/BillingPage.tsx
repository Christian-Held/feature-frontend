import { useMemo, useState } from 'react'

import { useAccountPlan, useUpdateAccountPlan } from '../../features/account/hooks'
import { CAP_WARNING_MESSAGE } from '../../features/account/constants'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Spinner } from '../../components/ui/Spinner'
import type { AccountPlanResponse } from '../../lib/api'
import { ApiError } from '../../lib/api'

const PLAN_OPTIONS: Array<{
  code: AccountPlanResponse['plan']
  title: string
  price: string
  description: string
  features: string[]
}> = [
  {
    code: 'FREE',
    title: 'Free',
    price: '$0/mo',
    description: 'Foundational access for prototyping and occasional automations.',
    features: ['Community support', 'Shared queue access', 'Usage analytics (basic)'],
  },
  {
    code: 'PRO',
    title: 'Pro',
    price: '$99/mo',
    description: 'Priority execution windows, deeper analytics, and premium support.',
    features: ['Priority scheduling', 'Advanced usage analytics', 'Dedicated support channel'],
  },
]

export function BillingPage() {
  const { data: currentPlan, isLoading } = useAccountPlan()
  const updatePlan = useUpdateAccountPlan()
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const activePlan = useMemo(() => currentPlan?.plan, [currentPlan])

  const handleSelect = (code: AccountPlanResponse['plan']) => {
    if (code === activePlan || updatePlan.isPending) {
      return
    }
    setStatusMessage(null)
    setErrorMessage(null)
    updatePlan.mutate(
      { plan: code },
      {
        onSuccess: (data) => {
          setStatusMessage(`Plan updated to ${data.name}`)
        },
        onError: (error) => {
          if (error instanceof ApiError) {
            if (error.status === 402) {
              setErrorMessage(CAP_WARNING_MESSAGE)
              return
            }
            setErrorMessage(error.message)
          } else {
            setErrorMessage('Unable to update plan right now. Please try again.')
          }
        },
      },
    )
  }

  return (
    <AppShell>
      <Header
        title="Billing Plan"
        description="Choose the subscription tier that matches your team’s automation workload."
      />
      <div className="flex-1 p-6">
        {isLoading ? (
          <div className="flex min-h-[240px] items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-950/40">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="space-y-6">
            {statusMessage && (
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-200">
                {statusMessage}
              </div>
            )}
            {errorMessage && (
              <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
                {errorMessage}
              </div>
            )}
            <div className="grid gap-4 md:grid-cols-2">
              {PLAN_OPTIONS.map((plan) => {
                const isActive = plan.code === activePlan
                const isPending = updatePlan.isPending && updatePlan.variables?.plan === plan.code
                return (
                  <button
                    key={plan.code}
                    type="button"
                    onClick={() => handleSelect(plan.code)}
                    disabled={isPending}
                    aria-label={`${plan.title} plan option`}
                    className={`group flex h-full flex-col justify-between rounded-2xl border p-6 text-left transition
                      ${
                        isActive
                          ? 'border-sky-400/70 bg-sky-500/10 text-white shadow-lg shadow-sky-900/40'
                          : 'border-slate-800/70 bg-slate-950/50 hover:border-sky-500/50 hover:bg-slate-900/60'
                      } ${isPending ? 'opacity-70' : ''}`}
                  >
                    <div className="space-y-4">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">{plan.title}</p>
                        <p className="mt-2 text-3xl font-bold text-white">{plan.price}</p>
                        <p className="mt-2 text-sm text-slate-300">{plan.description}</p>
                      </div>
                      <ul className="space-y-2 text-sm text-slate-300">
                        {plan.features.map((feature) => (
                          <li key={feature} className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-sky-400" aria-hidden="true" />
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="mt-6">
                      <span
                        className={`inline-flex items-center rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition
                          ${
                            isActive
                              ? 'bg-sky-500/20 text-sky-200'
                              : 'bg-slate-800/70 text-slate-200 group-hover:bg-sky-500/20 group-hover:text-sky-100'
                          }`}
                      >
                        {isActive ? 'Current Plan' : isPending ? 'Updating…' : 'Select Plan'}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}

export default BillingPage
