import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/react/24/outline'

import { clearSpendWarning, useSpendWarning } from '../../features/account/store'

export function SpendWarningBanner() {
  const { data } = useSpendWarning()

  if (!data?.active) {
    return null
  }

  return (
    <div className="border border-amber-500/40 bg-amber-500/10 text-amber-100">
      <div className="flex items-start justify-between gap-4 p-4">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 rounded-full bg-amber-500/20 p-2 text-amber-300">
            <ExclamationTriangleIcon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-semibold uppercase tracking-wide text-amber-200">Spend Limit Warning</p>
            <p className="text-sm text-amber-100/90">{data.message}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => clearSpendWarning()}
          className="rounded-md p-1 text-amber-200 transition hover:bg-amber-500/20 hover:text-white"
          aria-label="Dismiss spending limit warning"
        >
          <XMarkIcon className="h-5 w-5" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
