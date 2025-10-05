import { Tab } from '@headlessui/react'
import { Header } from '../components/layout/Header'
import { AppShell } from '../components/layout/AppShell'
import { EnvSettings } from '../components/settings/EnvSettings'
import { ModelSettings } from '../components/settings/ModelSettings'
import { twMerge } from 'tailwind-merge'

const tabs = [
  { name: 'Environment', component: EnvSettings },
  { name: 'Models', component: ModelSettings },
]

export function SettingsPage() {
  return (
    <AppShell>
      <Header
        title="Control Center"
        description="Manage environment credentials, API keys and model routing logic for your deployment."
      />
      <div className="flex-1 p-6">
        <Tab.Group>
          <Tab.List className="flex gap-3 rounded-2xl border border-slate-800/70 bg-slate-950/60 p-1">
            {tabs.map((tab) => (
              <Tab key={tab.name} className={({ selected }) =>
                twMerge(
                  'flex-1 rounded-xl px-4 py-2 text-sm font-medium transition',
                  selected
                    ? 'bg-slate-800 text-white shadow-inner shadow-slate-900'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60',
                )
              }>
                {tab.name}
              </Tab>
            ))}
          </Tab.List>
          <Tab.Panels className="mt-6 space-y-6">
            {tabs.map((tab) => (
              <Tab.Panel key={tab.name}>
                <tab.component />
              </Tab.Panel>
            ))}
          </Tab.Panels>
        </Tab.Group>
      </div>
    </AppShell>
  )
}
