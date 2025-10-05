import type { HTMLAttributes } from 'react'
import { twMerge } from 'tailwind-merge'

const statusStyles: Record<string, string> = {
  pending: 'bg-amber-500/20 text-amber-200 ring-1 ring-inset ring-amber-500/40',
  running: 'bg-sky-500/20 text-sky-200 ring-1 ring-inset ring-sky-500/40',
  completed: 'bg-emerald-500/20 text-emerald-200 ring-1 ring-inset ring-emerald-500/40',
  failed: 'bg-rose-500/20 text-rose-200 ring-1 ring-inset ring-rose-500/40',
  cancelled: 'bg-slate-600/30 text-slate-200 ring-1 ring-inset ring-slate-500/50',
  default: 'bg-slate-700/50 text-slate-200 ring-1 ring-inset ring-slate-600/70',
}

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof statusStyles
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={twMerge(
        'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide',
        statusStyles[variant] ?? statusStyles.default,
        className,
      )}
      {...props}
    />
  )
}
