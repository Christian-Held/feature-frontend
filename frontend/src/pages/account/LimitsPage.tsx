import { FormEvent, useEffect, useState } from 'react'

import { useAccountLimits, useUpdateAccountLimits } from '../../features/account/hooks'
import { CAP_WARNING_MESSAGE } from '../../features/account/constants'
import { AppShell } from '../../components/layout/AppShell'
import { Header } from '../../components/layout/Header'
import { Spinner } from '../../components/ui/Spinner'
import { ApiError } from '../../lib/api'

function formatCurrency(value: string) {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return '$0.00'
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(number)
}

export function LimitsPage() {
  const { data, isLoading } = useAccountLimits()
  const updateLimits = useUpdateAccountLimits()
  const [capInput, setCapInput] = useState('0.00')
  const [hardStop, setHardStop] = useState(false)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    if (data) {
      setCapInput(data.monthly_cap_usd)
      setHardStop(Boolean(data.hard_stop))
    }
  }, [data])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setStatusMessage(null)
    setErrorMessage(null)
    updateLimits.mutate(
      { monthly_cap_usd: capInput, hard_stop: hardStop },
      {
        onSuccess: (payload) => {
          setCapInput(payload.monthly_cap_usd)
          setHardStop(Boolean(payload.hard_stop))
          setStatusMessage('Spending limits updated successfully.')
        },
        onError: (error) => {
          if (error instanceof ApiError) {
            if (error.status === 402) {
              setErrorMessage(CAP_WARNING_MESSAGE)
              return
            }
            setErrorMessage(error.message)
          } else {
            setErrorMessage('Unable to update limits right now. Please try again.')
          }
        },
      },
    )
  }

  return (
    <AppShell>
      <Header
        title="Usage Limits"
        description="Manage monthly spend ceilings, set hard stops, and review current usage before launching more work."
      />
      <div className="flex-1 p-6">
        {isLoading ? (
          <div className="flex min-h-[240px] items-center justify-center rounded-2xl border border-slate-800/60 bg-slate-950/40">
            <Spinner size="lg" />
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
            <form
              onSubmit={handleSubmit}
              className="space-y-4 rounded-2xl border border-slate-800/60 bg-slate-950/50 p-6 shadow-inner shadow-slate-900/40"
            >
              <div>
                <label htmlFor="monthly-cap" className="text-sm font-medium text-slate-200">
                  Monthly spending cap (USD)
                </label>
                <div className="mt-2 flex items-center gap-3">
                  <span className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-slate-400">USD</span>
                  <input
                    id="monthly-cap"
                    name="monthly_cap_usd"
                    type="number"
                    min="0"
                    step="0.01"
                    value={capInput}
                    onChange={(event) => setCapInput(event.target.value)}
                    className="flex-1 rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
                  />
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  Set to 0.00 to allow usage only when triggered by administrators.
                </p>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-slate-800/60 bg-slate-900/50 p-4">
                <div>
                  <p className="text-sm font-semibold text-slate-200">Hard stop when cap reached</p>
                  <p className="text-xs text-slate-400">
                    When enabled, workflows pause immediately once spending hits the configured cap.
                  </p>
                </div>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={hardStop}
                    onChange={(event) => setHardStop(event.target.checked)}
                    className="peer sr-only"
                  />
                  <div className="peer h-6 w-11 rounded-full bg-slate-700 transition peer-checked:bg-sky-500">
                    <div className="h-5 w-5 translate-x-0.5 rounded-full bg-white transition peer-checked:translate-x-5" />
                  </div>
                </label>
              </div>

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

              <button
                type="submit"
                disabled={updateLimits.isPending}
                className="inline-flex items-center justify-center rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {updateLimits.isPending ? 'Saving…' : 'Save limits'}
              </button>
            </form>

            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-800/60 bg-slate-950/50 p-6 shadow-inner shadow-slate-900/40">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Current month</h3>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Used</span>
                    <span className="font-semibold text-white">{formatCurrency(data?.usage_usd ?? '0')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Cap</span>
                    <span className="font-semibold text-white">{formatCurrency(data?.monthly_cap_usd ?? '0')}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Remaining</span>
                    <span className="font-semibold text-white">{formatCurrency(data?.remaining_usd ?? '0')}</span>
                  </div>
                </div>
                {data?.cap_reached && (
                  <p className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-100">
                    {data.hard_stop
                      ? 'Hard stop is enabled. New jobs will be blocked until limits are adjusted.'
                      : 'Soft warning active. New jobs may continue, but additional spend will exceed your configured cap.'}
                  </p>
                )}
              </div>
              <div className="rounded-2xl border border-slate-800/60 bg-slate-950/40 p-6 text-xs text-slate-400">
                <p className="font-semibold text-slate-200">Forecast guidance</p>
                <p className="mt-2">
                  Budgets refresh at the start of each UTC calendar month. Adjust your cap if upcoming releases are expected to
                  increase workload volume.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  )
}

export default LimitsPage
