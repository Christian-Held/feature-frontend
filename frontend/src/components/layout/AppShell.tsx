import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      <Sidebar />
      <main className="flex-1 overflow-hidden">
        <div className="flex min-h-screen flex-col">{children}</div>
      </main>
    </div>
  )
}
