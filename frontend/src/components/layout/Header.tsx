import type { ReactNode } from 'react'
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline'
import { Input } from '../ui/Input'

interface HeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

export function Header({ title, description, actions }: HeaderProps) {
  return (
    <header className="flex flex-col gap-6 border-b border-slate-800/60 bg-slate-950/40 px-8 py-6 lg:flex-row lg:items-center lg:justify-between">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-white md:text-3xl">{title}</h1>
        {description && <p className="max-w-3xl text-sm text-slate-400">{description}</p>}
      </div>
      <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
        <div className="relative flex-1 sm:max-w-xs">
          <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-2.5 h-5 w-5 text-slate-500" />
          <Input className="pl-10" placeholder="Search jobs, files, models" />
        </div>
        {actions}
      </div>
    </header>
  )
}
