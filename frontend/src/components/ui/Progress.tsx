import { twMerge } from 'tailwind-merge'

interface ProgressProps {
  value: number
  srLabel?: string
}

export function Progress({ value, srLabel }: ProgressProps) {
  const clampedValue = Math.min(100, Math.max(0, Number.isFinite(value) ? value : 0))

  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-slate-800/70">
      {srLabel && <span className="sr-only">{srLabel}</span>}
      <div
        className={twMerge(
          'h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-500 transition-all duration-300',
        )}
        style={{ width: `${clampedValue}%` }}
        aria-hidden="true"
      />
    </div>
  )
}

export default Progress
