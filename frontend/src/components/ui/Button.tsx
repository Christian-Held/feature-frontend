import { forwardRef } from 'react'
import type { ButtonHTMLAttributes } from 'react'
import { twMerge } from 'tailwind-merge'

const baseStyles =
  'inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800/70 px-3 py-2 text-sm font-medium text-slate-100 shadow-sm transition hover:bg-slate-700 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent'

const variants = {
  primary:
    'border-transparent bg-gradient-to-r from-sky-500 to-indigo-500 text-slate-900 hover:from-sky-400 hover:to-indigo-400 focus-visible:outline-primary',
  secondary:
    'border-slate-600 bg-slate-700/40 text-slate-200 hover:bg-slate-600/60',
  outline:
    'border-slate-600 bg-transparent text-slate-200 hover:border-slate-400 hover:bg-slate-700/60',
  ghost: 'border-transparent bg-transparent text-slate-300 hover:bg-slate-700/60',
}

type Variant = keyof typeof variants

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={twMerge(baseStyles, variants[variant], className)}
        {...props}
      />
    )
  },
)

Button.displayName = 'Button'
