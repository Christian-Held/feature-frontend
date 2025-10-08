import { NavLink } from 'react-router-dom'
import { twMerge } from 'tailwind-merge'
import { Squares2X2Icon, Cog6ToothIcon, CreditCardIcon, ChartBarIcon, RocketLaunchIcon, BanknotesIcon } from '@heroicons/react/24/outline'

const navItems = [
  { name: 'Dashboard', to: '/', icon: Squares2X2Icon },
  { name: 'Subscription', to: '/account/subscription', icon: RocketLaunchIcon },
  { name: 'Billing', to: '/account/billing', icon: CreditCardIcon },
  { name: 'Payment History', to: '/billing/history', icon: BanknotesIcon },
  { name: 'Limits', to: '/account/limits', icon: ChartBarIcon },
  { name: 'Settings', to: '/settings', icon: Cog6ToothIcon },
]

export function Sidebar() {
  return (
    <aside className="flex w-60 flex-col gap-6 border-r border-slate-800/70 bg-slate-950/70 px-4 py-6">
      <div className="flex items-center gap-2 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-500 text-slate-900 font-bold">
          AI
        </div>
        <div>
          <p className="text-sm font-semibold text-white">AI Workbench</p>
          <p className="text-xs text-slate-400">Operations Console</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              twMerge(
                'flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition',
                'text-slate-300 hover:bg-slate-800/60 hover:text-white',
                isActive && 'bg-slate-800 text-white shadow-inner shadow-slate-900',
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.name}
          </NavLink>
        ))}
      </nav>
      <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3 text-xs text-slate-400">
        <p className="font-semibold text-slate-200">Status</p>
        <p>Backend ready. Live updates enabled.</p>
      </div>
    </aside>
  )
}
