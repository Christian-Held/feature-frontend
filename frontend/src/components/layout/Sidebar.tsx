import { NavLink, useNavigate } from 'react-router-dom'
import { twMerge } from 'tailwind-merge'
import { Squares2X2Icon, Cog6ToothIcon, CreditCardIcon, ChartBarIcon, RocketLaunchIcon, BanknotesIcon, ArrowRightOnRectangleIcon, UsersIcon, ClipboardDocumentListIcon, ChatBubbleBottomCenterTextIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '../../stores/authStore'
import { useSubscription } from '../../features/subscription/hooks'

const allNavItems = [
  { name: 'Dashboard', to: '/', icon: Squares2X2Icon, requiresPro: false, adminOnly: false },
  { name: 'AI Assistant', to: '/rag/websites', icon: ChatBubbleBottomCenterTextIcon, requiresPro: false, adminOnly: false },
  { name: 'Subscription', to: '/account/subscription', icon: RocketLaunchIcon, requiresPro: false, adminOnly: false },
  { name: 'Billing', to: '/account/billing', icon: CreditCardIcon, requiresPro: true, adminOnly: false },
  { name: 'Payment History', to: '/billing/history', icon: BanknotesIcon, requiresPro: true, adminOnly: false },
  { name: 'Limits', to: '/account/limits', icon: ChartBarIcon, requiresPro: true, adminOnly: false },
  { name: 'Settings', to: '/settings', icon: Cog6ToothIcon, requiresPro: false, adminOnly: false },
]

const adminNavItems = [
  { name: 'Admin: Users', to: '/admin/users', icon: UsersIcon, requiresPro: false, adminOnly: true },
  { name: 'Admin: Audit Logs', to: '/admin/audit-logs', icon: ClipboardDocumentListIcon, requiresPro: false, adminOnly: true },
]

export function Sidebar() {
  const navigate = useNavigate()
  const { clearAuth, user } = useAuthStore()
  const { data: subscriptionData } = useSubscription()

  // Admin users see everything, PRO users see everything, FREE users only see subscription
  const isPro = subscriptionData?.plan?.name === 'PRO'
  const isAdmin = user?.roles?.includes('superadmin')

  // Admins always see everything, otherwise check plan
  const canSeeAll = isAdmin || isPro

  // Filter regular nav items based on plan
  const filteredNavItems = canSeeAll
    ? allNavItems
    : allNavItems.filter(item => !item.requiresPro)

  // Add admin items if user is admin
  const navItems = isAdmin
    ? [...filteredNavItems, ...adminNavItems]
    : filteredNavItems

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <aside className="flex h-screen w-60 flex-col gap-6 border-r border-slate-800/70 bg-slate-950/70 px-4 py-6">
      <div className="flex items-center gap-2 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-sky-500 to-indigo-500 text-slate-900 font-bold">
          AI
        </div>
        <div>
          <p className="text-sm font-semibold text-white">AI Workbench</p>
          <p className="text-xs text-slate-400">Operations Console</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-2 overflow-y-auto">
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
      <div className="space-y-3">
        {user && (
          <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-3 text-xs">
            <p className="font-semibold text-slate-200 truncate">{user.email}</p>
            <p className="text-slate-400">
              {user.roles.includes('superadmin') ? 'Admin' : 'User'}
            </p>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-red-900/20 hover:text-red-400"
        >
          <ArrowRightOnRectangleIcon className="h-5 w-5" />
          Logout
        </button>
      </div>
    </aside>
  )
}
