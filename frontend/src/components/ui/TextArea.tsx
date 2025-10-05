import { forwardRef } from 'react'
import type { TextareaHTMLAttributes } from 'react'
import { twMerge } from 'tailwind-merge'

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={twMerge(
        'w-full rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/60',
        className,
      )}
      {...props}
    />
  ),
)

TextArea.displayName = 'TextArea'
