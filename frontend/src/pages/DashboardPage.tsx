import { useState } from 'react'
import { Header } from '../components/layout/Header'
import { AppShell } from '../components/layout/AppShell'
import { JobCreator } from '../components/dashboard/JobCreator'
import { JobDetails } from '../components/dashboard/JobDetails'
import { JobList } from '../components/dashboard/JobList'
import { FileBrowser } from '../components/dashboard/FileBrowser'
import { ConnectionPill } from '../components/dashboard/ConnectionPill'

export function DashboardPage() {
  const [selectedJobId, setSelectedJobId] = useState<string | undefined>()

  return (
    <AppShell>
      <Header
        title="Intelligence Dashboard"
        description="Coordinate workloads, tune models and browse generated outputs in real time."
        actions={<ConnectionPill />}
      />
      <div className="flex flex-1 flex-col gap-6 p-6 xl:grid xl:grid-cols-[320px_1fr_360px]">
        <div className="space-y-6">
          <JobCreator onJobCreated={(job) => setSelectedJobId(job.id)} />
          <JobList selectedJobId={selectedJobId} onSelect={(job) => setSelectedJobId(job.id)} />
        </div>
        <JobDetails jobId={selectedJobId} />
        <FileBrowser />
      </div>
    </AppShell>
  )
}
