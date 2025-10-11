import { forwardRef } from 'react'
import type { ButtonHTMLAttributes } from 'react'
import { twMerge } from 'tailwind-merge'

const baseStyles =
  'inline-flex items-center justify-center gap-2 rounded-lg border font-medium shadow-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60'

const variants = {
  primary:
    'border-transparent bg-gradient-to-r from-sky-500 to-indigo-500 text-slate-900 hover:from-sky-400 hover:to-indigo-400',
  secondary:
    'border-slate-600 bg-slate-700/40 text-slate-200 hover:bg-slate-600/60',
  outline:
    'border-slate-600 bg-transparent text-slate-200 hover:border-slate-400 hover:bg-slate-700/60',
  ghost: 'border-transparent bg-transparent text-slate-300 hover:bg-slate-700/60',
  danger:
    'border-red-500/50 bg-red-500/10 text-red-200 hover:bg-red-500/20 hover:text-red-100 focus-visible:outline-red-400',
}

const sizes = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-3 py-2 text-sm',
  lg: 'px-4 py-2.5 text-base',
}

type Variant = keyof typeof variants
type Size = keyof typeof sizes

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={twMerge(baseStyles, sizes[size], variants[variant], className)}
        {...props}
      />
    )
  },
)

Button.displayName = 'Button'
