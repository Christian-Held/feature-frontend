import type { HTMLAttributes } from 'react'
import { twMerge } from 'tailwind-merge'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={twMerge(
        'rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-panel backdrop-blur-sm',
        className,
      )}
      {...props}
    />
  )
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={twMerge('mb-4 flex items-start justify-between gap-4', className)} {...props} />
  )
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={twMerge('text-lg font-semibold text-white', className)} {...props} />
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={twMerge('text-sm text-slate-400', className)} {...props} />
  )
}
